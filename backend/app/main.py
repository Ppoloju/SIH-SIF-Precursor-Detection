"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, evaluation, feedback, ingest, reports, review
from app.config import get_settings
from app.models.db import SessionLocal, init_db
from app.models.entities import Analysis
from app.data.seed import seed_all_if_empty
from app.services import adaptive
from app.services.rule_classifier import classify_rule
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def backfill_missing_rules(db) -> int:
    """Assign a text-derived canonical rule to legacy unclassified analyses."""
    rows = db.execute(
        select(Analysis).where(Analysis.life_saving_rule.is_(None))
    ).scalars().all()
    updated = 0
    for analysis in rows:
        rule, _confidence = classify_rule([], analysis.report.report_text if analysis.report else "")
        if rule:
            analysis.life_saving_rule = rule
            updated += 1
    if updated:
        db.commit()
    return updated


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: create tables, seed the demo dataset when empty, and load
    any learned reviewer signals from previous training runs."""
    init_db()
    db = SessionLocal()
    try:
        seed_all_if_empty(db)
        updated = backfill_missing_rules(db)
        if updated:
            logger.info("Backfilled canonical Life-Saving Rules for %d analyses.", updated)
        adaptive.reload_active(db)
    except Exception as exc:  # noqa: BLE001 — never crash the API because of seeding
        logger.warning("Startup seeding/signals skipped (%s). The API will still run.", exc)
    finally:
        db.close()
    # Best-effort preload of the real-time ML imputation model (training split
    # only) so the first analyze/ingest call is already fast. Never fatal.
    try:
        from app.services import ml_inference

        ml_inference.status()
    except Exception as exc:  # noqa: BLE001
        logger.info("ML imputation model not preloaded (%s) — will lazy-load.", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI/NLP engine to detect Serious Injury & Fatality (SIF) precursors in "
        "Unsafe-Act / Unsafe-Condition and Near-Miss safety reports. Prototype."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(review.router)
app.include_router(analytics.router)
app.include_router(ingest.router)
app.include_router(feedback.router)
app.include_router(evaluation.router)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Health check used to verify the backend is running."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_available": bool(settings.groq_api_key),
        "database": "postgresql" if settings.database_url.startswith(("postgresql", "postgres+")) else "sqlite",
    }


@app.get("/", tags=["system"], include_in_schema=False)
def root() -> dict:
    return {"message": "SIH SIF Precursor Detection API", "docs": "/docs", "health": "/api/health"}