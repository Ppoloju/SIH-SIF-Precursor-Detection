"""Generic dataset ingestion for the SIF pipeline.

Works with ANY tabular safety-report dataset — including HSSE platform
exports with columns like ``Report_id / Report_type / Site_name /
Location_detail / Activity / Hazard_category / Description`` — not only the
synthetic demo set. Responsibilities:

* Parse CSV / JSON / XLSX uploads (XLSX requires optional ``openpyxl``).
* Auto-map arbitrary column names to canonical fields
  (``text``, ``title``, ``date``, ``site``, ``activity``, ``report_type``).
* Normalize each row (date parsing, string cells, combined title+text,
  site + location-detail merging).
* Run every row through the standard analysis pipeline and persist
  report + analysis in batches — committed progressively so the frontend can
  watch processing progress in the database (``Report.processing_status``,
  ``IngestJob`` counters).

Imports can run inline (``ingest_rows``) or as a background job
(``start_import_job`` -> ``GET /api/ingest/jobs/{id}``).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import threading
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import SessionLocal
from app.models.entities import Analysis, IngestJob, Report
from app.services.analysis_pipeline import analyze_report

logger = logging.getLogger(__name__)

# Canonical field -> header it was read from (used for provenance only).
CANONICALS = ["text", "title", "date", "site", "activity", "report_type"]

MAX_REPORT_TEXT = 20_000
MAX_ROWS = 10_000
_JOB_COMMIT_EVERY = 10  # how often job progress is committed to the database

# ---------------------------------------------------------------------------
# Header synonym scoring (normalized headers: lowercase, no spaces/punct)
# ---------------------------------------------------------------------------

SYNONYMS: dict[str, list[tuple[str, int]]] = {
    "text": [
        ("what happened", 110),
        ("report", 100),
        ("description", 95),
        ("narrative", 95),
        ("observation", 90),
        ("incident detail", 85),
        ("occurrence", 75),
        ("details", 75),
        ("text", 70),
        ("statement", 70),
        ("summary", 65),
        ("remarks", 60),
        ("comments", 55),
        ("notes", 50),
    ],
    "title": [
        ("title", 100),
        ("subject", 90),
        ("headline", 80),
        ("heading", 75),
        ("short description", 60),
    ],
    "date": [
        ("date", 90),
        ("reported on", 95),
        ("report date", 95),
        ("observation date", 95),
        ("incident date", 95),
        ("date of report", 95),
        ("date of observation", 95),
        ("date of incident", 95),
        ("reported date", 95),
        ("when", 40),
        ("created on", 70),
        ("created at", 60),
    ],
    "site": [
        ("site", 100),
        ("site name", 120),
        ("location", 95),
        ("plant", 90),
        ("facility", 85),
        ("installation", 85),
        ("area", 60),
        ("region", 60),
        ("unit", 45),
        ("department", 45),
        ("place", 45),
        ("work location", 100),
        ("location of work", 100),
        ("location name", 100),
    ],
    "activity": [
        ("activity", 95),
        ("nature of work", 110),
        ("type of work", 100),
        ("type of job", 100),
        ("kind of work", 100),
        ("task", 75),
        ("job", 65),
        ("operation", 70),
        ("work type", 85),
        ("activity performed", 95),
        ("work performed", 85),
        ("work", 40),
    ],
    "report_type": [
        ("report type", 110),
        ("type of report", 110),
        ("observation type", 105),
        ("incident type", 105),
        ("near miss type", 105),
        ("category", 95),
        ("classification", 90),
        ("type", 70),
        ("kind", 60),
        ("nature of report", 90),
    ],
}

# Free-text hints used by the fallback when no text column is recognized.
_TEXT_HINTS = ["report", "description", "narrative", "observation", "detail", "summary"]

# Normalized keywords so multi-word synonyms match space-free headers.
_SYNONYMS_NORM: dict[str, list[tuple[str, int]]] = {
    canonical: [(re.sub(r"[^a-z0-9]", "", kw.lower()), wt) for kw, wt in syns]
    for canonical, syns in SYNONYMS.items()
}


def normalize_header(value: str) -> str:
    """Lowercase and strip punctuation/spacing for matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _score_header(norm: str, keyword_norm: str, weight: int) -> int:
    if norm == keyword_norm:
        return weight * 2
    if keyword_norm in norm:
        return weight
    if len(keyword_norm) > 5 and len(norm) > 4 and norm in keyword_norm:
        return weight // 2
    return 0


def _auto_map_columns(headers: list[str]) -> dict[str, str]:
    """Return canonical -> best header. Global greedy assignment so a 'type'
    column never becomes the report text and Site_name wins over a generic
    Location_detail column for the ``site`` slot."""
    hits: list[tuple[int, str, str]] = []
    for header in headers:
        norm = normalize_header(header)
        if not norm:
            continue
        for canonical, synonyms in _SYNONYMS_NORM.items():
            score = max(_score_header(norm, kw, wt) for kw, wt in synonyms)
            if score > 0:
                hits.append((score, canonical, header))

    hits.sort(key=lambda t: t[0], reverse=True)
    mapping: dict[str, str] = {}
    used_headers: set[str] = set()
    for score, canonical, header in hits:  # noqa: B007
        if canonical in mapping or header in used_headers:
            continue
        mapping[canonical] = header
        used_headers.add(header)

    if "text" not in mapping:
        mapping["text"] = _fallback_text_column(headers, used_headers)
    return mapping


def _fallback_text_column(headers: list[str], used: set[str]) -> str | None:
    for header in headers:
        if header in used:
            continue
        norm = normalize_header(header)
        for hint in _TEXT_HINTS:
            if hint in norm and len(norm) >= len(hint):
                return header
    for header in headers:  # last resort: first unused column
        if header not in used:
            return header
    return None


def _location_detail_column(headers: list[str], mapping: dict[str, str | None]) -> str | None:
    """HSSE exports often have Site_name + Location_detail. Keep the extra
    detail and merge it into the site value at normalize time."""
    for header in headers:
        if header in mapping.values():
            continue
        norm = normalize_header(header)
        if "location" in norm and ("detail" in norm or "specific" in norm):
            return header
    return None


def resolve_mapping(
    headers: list[str],
    override: Optional[dict[str, str]] = None,
) -> dict[str, str | None]:
    """Effective mapping canonical -> column (or None if disabled)."""
    auto = _auto_map_columns(headers)
    effective: dict[str, str | None] = {}
    for canonical in CANONICALS:
        if override and canonical in override:
            val = (override.get(canonical) or "").strip()
            if val == "__none__":
                effective[canonical] = None
            elif val in headers:
                effective[canonical] = val
            else:
                effective[canonical] = auto.get(canonical)
        else:
            effective[canonical] = auto.get(canonical)
    return effective


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value).strip()


_DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y",
    "%d.%m.%Y", "%Y.%m.%d", "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
    "%d-%b-%Y", "%d-%B-%Y", "%b %d, %Y", "%B %d, %Y", "%d %b, %Y", "%Y%m%d",
]


def parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s or s.lower() in {"na", "n/a", "-", "--", "null", "none", "nan"}:
        return None
    iso = re.split(r"[T ]", s, maxsplit=1)[0].strip()
    for fmt in _DATE_FORMATS:
        for candidate in ({iso, s} if iso != s else {iso}):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


def parse_rows(filename: str, raw: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse an uploaded file into (headers, rows-as-dicts)."""
    name = (filename or "").lower()

    if name.endswith(".json"):
        payload = json.loads(raw.decode("utf-8-sig", errors="replace"))
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            payload = payload["rows"]
        if not isinstance(payload, list) or not payload:
            raise ValueError("JSON must be an array of row objects (or {rows: [...]})")
        if not all(isinstance(r, dict) for r in payload):
            raise ValueError("JSON rows must be objects with column names as keys")
        return list(payload[0].keys()), payload

    if name.endswith(".xlsx"):
        return _parse_xlsx(raw)

    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    first_line = lines[0] if lines else ""
    dialect: Any = csv.excel_tab if ("\t" in first_line and "," not in first_line) else csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [dict(r) for r in reader if any((v or "").strip() for v in r.values())]
    if not rows:
        raise ValueError("CSV has no data rows")
    return list(rows[0].keys()), rows


def _parse_xlsx(raw: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        import openpyxl  # optional dependency
    except ImportError as exc:  # pragma: no cover
        raise ValueError(
            "XLSX support requires 'openpyxl' — pip install openpyxl, or export the sheet to CSV/JSON."
        ) from exc
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    if not header_row:
        raise ValueError("XLSX sheet has no header row")
    headers = [str(h).strip() if h is not None else f"column_{i}" for i, h in enumerate(header_row)]
    rows: list[dict[str, Any]] = []
    for values in rows_iter:
        row = {headers[i]: values[i] for i in range(len(headers)) if i < len(values)}
        if any((v is not None and str(v).strip()) for v in values or []):
            rows.append(row)
    if not rows:
        raise ValueError("XLSX has no data rows")
    return headers, rows


# ---------------------------------------------------------------------------
# Row normalization + import
# ---------------------------------------------------------------------------

def normalize_row(row: dict[str, Any], mapping: dict[str, str | None],
                  headers: Optional[list[str]] = None) -> dict[str, Any]:
    """Map an arbitrary source row onto canonical report fields."""

    def field(canonical: str) -> str:
        column = mapping.get(canonical)
        if not column:
            return ""
        return _cell(row.get(column))

    title = field("title")
    body = field("text")

    parts: list[str] = []
    if title and title != body:
        parts.append(title.rstrip(".") + ".")
    if body:
        parts.append(body)
    text = " ".join(parts).strip()

    site = field("site")
    if site and headers:
        detail_col = _location_detail_column(headers, mapping)
        if detail_col:
            detail = _cell(row.get(detail_col))
            if detail and detail.lower() not in {"na", "n/a", "-", "nil", "none"}:
                site = f"{site} · {detail}"[:128]

    return {
        "report_text": text[:MAX_REPORT_TEXT],
        "title": title,
        "report_type": field("report_type")[:32] or None,
        "date": parse_date(row.get(mapping["date"])) if mapping.get("date") else None,
        "site": site[:128] or None,
        "activity": field("activity")[:128] or None,
    }


def next_report_id(db: Session) -> str:
    last = db.execute(select(Report.report_id).order_by(Report.id.desc()).limit(1)).scalar()
    if not last:
        return "RPT-0001"
    try:
        num = int(last.split("-")[-1]) + 1
    except ValueError:
        num = 1
    return f"RPT-{num:04d}"


def _import_one_row(
    db: Session,
    raw_row: dict[str, Any],
    mapping: dict[str, str | None],
    source: str,
    headers: Optional[list[str]] = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Create + analyze a single report row. Returns status info."""
    norm = normalize_row(raw_row, mapping, headers)
    text = norm["report_text"]
    if not text:
        return {"ok": False, "skipped": True, "error": "no text column value"}

    report = Report(
        report_id=next_report_id(db),
        report_text=text,
        report_type=norm["report_type"],
        date=norm["date"],
        site=norm["site"],
        activity=norm["activity"],
        is_demo=False,
        source=source,
        processing_status="pending",
    )
    db.add(report)
    db.flush()

    try:
        result = analyze_report(text, use_llm=use_llm)
    except Exception as exc:  # noqa: BLE001 — row-level isolation
        report.processing_status = "failed"
        return {"ok": False, "skipped": False, "error": f"{type(exc).__name__}: {exc}"[:400],
                "report": report}

    db.add(
        Analysis(
            report_id=report.id,
            sif_potential=result["sif_potential"],
            confidence=result["confidence"],
            priority=result["priority"],
            hazard=result["hazard"],
            potential_consequence=result["potential_consequence"],
            barrier_failure=result["barrier_failure"],
            life_saving_rule=result["life_saving_rule"],
            activity=result["activity"],
            evidence=result["evidence"],
            explanation=result["explanation"],
            recommended_follow_up=result["recommended_follow_up"],
            summary=result.get("summary"),
            suggested_actions=result.get("suggested_actions"),
            languages=result.get("languages"),
            uncertainty_note=result.get("uncertainty_note"),
            model=result["model"],
        )
    )
    report.processing_status = "analyzed"
    return {"ok": True, "skipped": False, "report": report,
            "sif": result["sif_potential"], "high": result["priority"] == "HIGH"}


def ingest_rows(
    db: Session,
    rows: list[dict[str, Any]],
    mapping: Optional[dict[str, str | None]] = None,
    source: str = "upload",
    use_llm: bool = True,
    headers: Optional[list[str]] = None,
    job_id: Optional[int] = None,
) -> dict[str, Any]:
    """Import arbitrary rows through the full pipeline and persist everything.

    When ``job_id`` is given the ``IngestJob`` counters are updated as batches
    are committed so callers can poll processing progress.
    """
    if not rows:
        raise ValueError("No rows to import")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"Too many rows: {len(rows)} (max {MAX_ROWS})")

    source = (source or "upload").strip()[:64] or "upload"
    if headers is None:
        headers = list(rows[0].keys())
    if mapping is None:
        mapping = resolve_mapping(headers)

    imported = 0
    sif_count = 0
    high_count = 0
    skipped_empty = 0
    failures: list[dict[str, Any]] = []
    first_report_id: str | None = None
    processed = 0

    def _sync_job() -> None:
        if job_id is None:
            return
        db.execute(
            IngestJob.__table__.update()
            .where(IngestJob.id == job_id)
            .values(
                processed=processed,
                imported=imported,
                skipped_empty=skipped_empty,
                failed_count=len(failures),
                sif_potential=sif_count,
                high_priority=high_count,
                failures=failures[-20:] or None,
                first_report_id=first_report_id,
            )
        )
        db.commit()

    for i, raw_row in enumerate(rows, start=1):
        try:
            outcome = _import_one_row(db, raw_row, mapping, source, headers, use_llm)
        except Exception as exc:  # noqa: BLE001 — never fail the whole import
            outcome = {"ok": False, "skipped": False, "error": f"{type(exc).__name__}: {exc}"[:400]}
        processed += 1

        if outcome.get("skipped"):
            skipped_empty += 1
            continue
        if not outcome.get("ok"):
            failures.append({"row": i, "error": outcome.get("error", "unknown error")[:400]})
            db.flush()  # persist failed report (if any) so status is visible
            if job_id is None and i % 50 == 0:
                db.commit()
            continue

        imported += 1
        first_report_id = first_report_id or outcome["report"].report_id
        if outcome.get("sif"):
            sif_count += 1
        if outcome.get("high"):
            high_count += 1

        if job_id is not None:
            if i % _JOB_COMMIT_EVERY == 0:
                db.commit()
                _sync_job()
        elif i % 50 == 0:
            db.commit()

    db.commit()
    if job_id is not None:
        _sync_job()

    return {
        "status": "ok",
        "rows_total": len(rows),
        "imported": imported,
        "skipped_empty": skipped_empty,
        "failed": failures,
        "sif_potential": sif_count,
        "high_priority": high_count,
        "source": source,
        "first_report_id": first_report_id,
        "mapping": mapping,
        "note": (
            "Each row was mapped onto report fields and run through the SIF pipeline. "
            "Reports are stored with source provenance (not demo data)."
        ),
    }


# ---------------------------------------------------------------------------
# Background import jobs (progress persisted in PostgreSQL)
# ---------------------------------------------------------------------------

def create_import_job(
    rows: list[dict[str, Any]],
    mapping: Optional[dict[str, str | None]] = None,
    source: str = "upload",
    filename: Optional[str] = None,
    headers: Optional[list[str]] = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Create an ``IngestJob`` row, then process the rows in a background
    thread, committing batches so the DB + UI show live progress."""
    db = SessionLocal()
    try:
        if headers is None:
            headers = list(rows[0].keys()) if rows else []
        if mapping is None:
            mapping = resolve_mapping(headers)
        job = IngestJob(
            status="running",
            source=(source or "upload").strip()[:64] or "upload",
            filename=filename,
            rows_total=len(rows),
            mapping={k: v for k, v in mapping.items()},
        )
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    def _worker() -> None:
        work_db = SessionLocal()
        try:
            summary = ingest_rows(
                work_db,
                rows,
                mapping={k: v for k, v in mapping.items()},
                source=source,
                use_llm=use_llm,
                headers=headers,
                job_id=job_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Import job %d failed", job_id)
            with SessionLocal() as err_db:
                job = err_db.get(IngestJob, job_id)
                if job:
                    job.status = "error"
                    job.error = f"{type(exc).__name__}: {exc}"[:2000]
                    job.finished_at = datetime.utcnow()
                    err_db.commit()
            return
        finally:
            work_db.close()

        with SessionLocal() as done_db:
            job = done_db.get(IngestJob, job_id)
            if job:
                job.status = "done"
                job.finished_at = datetime.utcnow()
                done_db.commit()

    threading.Thread(target=_worker, daemon=True, name=f"ingest-{job_id}").start()
    return {
        "job_id": job_id,
        "status": "running",
        "rows_total": len(rows),
        "source": (source or "upload").strip()[:64] or "upload",
        "filename": filename,
        "mapping": {k: v for k, v in mapping.items()},
    }


def job_summary(db: Session, job_id: int) -> dict[str, Any] | None:
    job = db.get(IngestJob, job_id)
    if job is None:
        return None
    return {
        "job_id": job.id,
        "status": job.status,
        "rows_total": job.rows_total,
        "processed": job.processed,
        "imported": job.imported,
        "skipped_empty": job.skipped_empty,
        "failed_count": job.failed_count,
        "sif_potential": job.sif_potential,
        "high_priority": job.high_priority,
        "first_report_id": job.first_report_id,
        "mapping": job.mapping,
        "failures": (job.failures or [])[-10:],
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "note": "Live job progress is persisted in the database as rows are processed.",
    }
