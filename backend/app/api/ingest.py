"""Ingestion API — get ANY safety-report dataset (e.g. an HSSE export) into the system.

Flow (works with arbitrary columns — nothing assumes the demo schema):

1. ``POST /api/ingest/file/preview`` — upload CSV / XLSX / JSON; the backend
   detects the column mapping and shows how the first rows will be parsed.
   No data is written.
2. ``POST /api/ingest/file`` — start an import job. The file is parsed, every
   row runs through the full SIF pipeline, and rows are committed to the
   database in batches — so the DB (and frontend) show live progress.
3. ``GET  /api/ingest/jobs/{id}`` — poll processing progress (persisted in
   PostgreSQL: counters + per-report ``processing_status``).
4. ``POST /api/ingest/rows`` — import raw JSON rows the same way (scripts/APIs).

Analytics derive from the database, so the dashboard reflects imports as soon
as batches commit.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db import get_db
from app.models.entities import IngestJob
from app.services.ingest import (
    CANONICALS,
    MAX_ROWS,
    create_import_job,
    job_summary,
    normalize_row,
    parse_rows,
    resolve_mapping,
)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

MAX_FILE_BYTES = 15 * 1024 * 1024  # 15 MB
SUPPORTED_EXTENSIONS = (".csv", ".tsv", ".txt", ".json", ".xlsx")

settings = get_settings()


class RowsImportRequest(BaseModel):
    """Import raw JSON rows (any keys) with an optional mapping override."""

    rows: list[dict[str, Any]] = Field(min_length=1, max_length=MAX_ROWS)
    field_mapping: Optional[dict[str, str]] = None
    source: Optional[str] = Field(default=None, max_length=64)


async def _read_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not any(name.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use CSV, TSV, TXT, JSON or XLSX.",
        )
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 15 MB)")
    return data


def _parse_mapping(form_value: Optional[str]) -> dict[str, str]:
    if not form_value or not form_value.strip():
        return {}
    try:
        parsed = json.loads(form_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"field_mapping is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="field_mapping must be a JSON object")
    return {k: str(v) for k, v in parsed.items()}


def _preview_payload(
    headers: list[str],
    rows: list[dict[str, Any]],
    override: Optional[dict[str, str]],
) -> dict[str, Any]:
    mapping = resolve_mapping(headers, override)
    samples = []
    for row in rows[:5]:
        norm = normalize_row(row, mapping, headers)
        samples.append(
            {
                "text": (norm["report_text"] or "")[:180] or None,
                "report_type": norm["report_type"],
                "date": norm["date"].isoformat() if norm["date"] else None,
                "site": norm["site"],
                "activity": norm["activity"],
            }
        )
    return {
        "columns": headers,
        "mapping": mapping,
        "canonicals": CANONICALS,
        "total_rows": len(rows),
        "samples": samples,
        "note": (
            "Shown before import — nothing is written yet. Columns map to "
            "canonical fields; empty metadata is fully inferred from text "
            "during analysis."
        ),
    }


@router.post("/file/preview", summary="Preview how an uploaded dataset will be mapped")
async def preview_file(
    file: UploadFile = File(...),
    field_mapping: Optional[str] = Form(default=None, description="Optional JSON override, e.g. {\"text\": \"Narrative\"}"),
):
    data = await _read_upload(file)
    try:
        headers, rows = parse_rows(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _preview_payload(headers, rows, _parse_mapping(field_mapping))


@router.post("/file", summary="Start an import job for an uploaded dataset file")
async def import_file(
    file: UploadFile = File(...),
    field_mapping: Optional[str] = Form(default=None),
    source: Optional[str] = Form(default=None, max_length=64),
):
    data = await _read_upload(file)
    try:
        headers, rows = parse_rows(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    mapping = resolve_mapping(headers, _parse_mapping(field_mapping))
    filename = (file.filename or "")[:255]
    src = (source or file.filename or "upload")[:64]
    return create_import_job(
        rows,
        mapping=mapping,
        source=f"upload:{src}",
        filename=filename,
        headers=headers,
        use_llm=bool(settings.groq_api_key),
    )


@router.post("/rows", summary="Start an import job for JSON rows")
def import_rows(
    payload: RowsImportRequest,
):
    rows = payload.rows
    headers = list(rows[0].keys()) if rows else []
    mapping = resolve_mapping(headers, payload.field_mapping)
    return create_import_job(
        rows,
        mapping=mapping,
        source=payload.source or "upload",
        headers=headers,
        use_llm=bool(settings.groq_api_key),
    )


@router.get("/jobs/{job_id}", summary="Poll import job progress")
def get_job(job_id: int, db: Session = Depends(get_db)):
    result = job_summary(db, job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    return result


@router.get("/jobs", summary="Recent import jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.execute(
        select(IngestJob).order_by(IngestJob.id.desc()).limit(10)
    ).scalars().all()
    return [
        {
            "job_id": j.id,
            "status": j.status,
            "source": j.source,
            "filename": j.filename,
            "rows_total": j.rows_total,
            "processed": j.processed,
            "imported": j.imported,
            "failed_count": j.failed_count,
            "sif_potential": j.sif_potential,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in jobs
    ]
