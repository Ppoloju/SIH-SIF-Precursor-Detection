"""Reports API — ingestion, analysis, retrieval."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.db import get_db
from app.models.entities import Analysis, Report, Review
from app.schemas.reports import (
    AnalysisResultOut,
    AnalyzeRequest,
    ReportCreate,
    ReportDetailOut,
    ReportOut,
)
from app.services.analysis_pipeline import analyze_report
from app.services.similarity import find_similar

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Similarity score above which the top match is flagged as a possible
# duplicate (near-identical wording => same event reported twice / a file
# imported twice). Genuinely similar-but-distinct precursors score lower
# because the engine caps shared-concept bonuses well below this.
DUP_SIMILARITY = 0.88


def _next_report_id(db: Session) -> str:
    last = db.execute(
        select(Report.report_id).order_by(Report.id.desc()).limit(1)
    ).scalar()
    if not last:
        return "RPT-0001"
    try:
        num = int(last.split("-")[-1]) + 1
    except ValueError:
        num = 1
    return f"RPT-{num:04d}"


def _store_analysis(db: Session, report: Report, result: dict) -> Analysis:
    analysis = Analysis(
        report_id=report.id,
        sif_potential=result["sif_potential"],
        confidence=result["confidence"],
        priority=result["priority"],
        hazard=result["hazard"],
        potential_consequence=result["potential_consequence"],
        barrier_failure=result["barrier_failure"],
        life_saving_rule=result["life_saving_rule"],
        activity=result["activity"],
        location=result.get("location"),
        equipment=result.get("equipment"),
        unsafe_type=result.get("unsafe_type"),
        rule_conditions=result.get("rule_conditions"),
        evidence=result["evidence"],
        explanation=result["explanation"],
        recommended_follow_up=result["recommended_follow_up"],
        summary=result.get("summary"),
        suggested_actions=result.get("suggested_actions"),
        languages=result.get("languages"),
        uncertainty_note=result.get("uncertainty_note"),
        model=result["model"],
    )
    db.add(analysis)
    return analysis


def _load_detail(db: Session, report_id: int, similar: bool = True) -> ReportDetailOut:
    report = db.execute(
        select(Report)
        .options(selectinload(Report.analysis), selectinload(Report.reviews))
        .where(Report.id == report_id)
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    review = report.reviews[-1] if report.reviews else None
    similar_reports = (
        find_similar(report, db=db, limit=5) if similar and report.analysis else []
    )
    # Enrich every match with its site + latest HSE review state so the UI can
    # tell "a similar case that was solved at another site" apart from one
    # that is still open — the basis of the site-A → site-B learning view.
    if similar_reports:
        ids = [s["id"] for s in similar_reports]
        matched = db.execute(
            select(Report)
            .options(selectinload(Report.reviews))
            .where(Report.id.in_(ids))
        ).scalars().all()
        meta: dict[int, dict] = {}
        for rep in matched:
            last = rep.reviews[-1] if rep.reviews else None
            meta[rep.id] = {
                "site": rep.site,
                "decision": last.decision if last else None,
                "reviewer": last.reviewer if last else None,
                "comments": last.comments if last else None,
                "corrected_rule": last.corrected_rule if last else None,
                "corrected_priority": last.corrected_priority if last else None,
                "reviewed_at": (
                    last.reviewed_at.isoformat() if last and last.reviewed_at else None
                ),
            }
        similar_reports = [{**s, **meta.get(s["id"], {})} for s in similar_reports]

    # Possible duplicate = the closest match is a near-copy of this report.
    duplicate_of = None
    if similar_reports and similar_reports[0]["similarity"] >= DUP_SIMILARITY:
        duplicate_of = similar_reports[0]
    return ReportDetailOut(
        **ReportOut.model_validate(report).model_dump(),
        analysis=report.analysis,
        review=review,
        review_status=review.decision if review else "pending",
        similar_reports=similar_reports,
        duplicate_of=duplicate_of,
    )


@router.post("/analyze", response_model=dict, summary="Analyze a safety report (optionally store it)")
def analyze(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
):
    """Run the SIF pipeline on a report.

    With `store=true` (default) the report + analysis are persisted and the
    full detail is returned. With `store=false` only the analysis result is
    returned (useful for live preview).
    """
    result = analyze_report(payload.report_text, use_llm=True)

    if not payload.store:
        return {
            "report": None,
            "analysis": AnalysisResultOut(**result),
            "stored": False,
        }

    report = Report(
        report_id=_next_report_id(db),
        report_text=payload.report_text,
        report_type=payload.report_type,
        date=payload.date,
        site=payload.site,
        activity=payload.activity,
        is_demo=False,
        source="manual",
    )
    db.add(report)
    db.flush()
    _store_analysis(db, report, result)
    db.commit()

    return {"report": _load_detail(db, report.id), "analysis": AnalysisResultOut(**result), "stored": True}


@router.post("", response_model=ReportDetailOut, status_code=201, summary="Create and analyze a report")
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
):
    result = analyze_report(payload.report_text, use_llm=True)
    report = Report(
        report_id=_next_report_id(db),
        report_text=payload.report_text,
        report_type=payload.report_type,
        date=payload.date,
        site=payload.site,
        activity=payload.activity,
        is_demo=False,
        source="manual",
    )
    db.add(report)
    db.flush()
    _store_analysis(db, report, result)
    db.commit()
    return _load_detail(db, report.id)


@router.get("", response_model=list[ReportDetailOut], summary="List reports with optional filters")
def list_reports(
    site: str | None = Query(default=None),
    activity: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    rule: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sif: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="Free-text search"),
    source: str | None = Query(default=None, description="Source file or dataset"),
    hazard: str | None = Query(default=None, description="Hazard (exact match)"),
    barrier: str | None = Query(default=None, description="Barrier failure contains"),
    limit: int = Query(default=500, le=10000),
    db: Session = Depends(get_db),
):
    # Build base query with optimized joins
    stmt = (
        select(Report)
        .options(selectinload(Report.analysis), selectinload(Report.reviews))
        .order_by(Report.date.desc().nullslast(), Report.id.desc())
    )
    
    # Apply filters efficiently
    if site:
        stmt = stmt.where(Report.site.ilike(f"%{site}%"))
    if activity:
        stmt = stmt.where(Report.activity.ilike(f"%{activity}%"))
    if q:
        stmt = stmt.where(Report.report_text.ilike(f"%{q}%"))
    if source:
        stmt = stmt.where(Report.source == source)
    
    # Join with Analysis only when needed for filters
    needs_analysis_join = (
        sif is not None
        or priority is not None
        or rule is not None
        or hazard is not None
        or barrier is not None
    )
    if needs_analysis_join:
        stmt = stmt.join(Analysis, Analysis.report_id == Report.id)
        if sif is not None:
            stmt = stmt.where(Analysis.sif_potential == sif)
        if priority:
            stmt = stmt.where(Analysis.priority == priority.upper())
        if rule:
            stmt = stmt.where(Analysis.life_saving_rule == rule)
        if hazard:
            stmt = stmt.where(Analysis.hazard == hazard)
        if barrier:
            # JSON arrays are not portably comparable; a cast-to-text contains
            # is good enough for a contains filter on this data volume.
            stmt = stmt.where(
                Analysis.barrier_failure.cast(String).ilike(f"%{barrier}%")
            )

    # Optimize status filtering with subquery instead of any()
    if status:
        if status == "pending":
            # Use NOT EXISTS for better performance than any()
            stmt = stmt.where(~exists().where(Review.report_id == Report.id))
        else:
            stmt = stmt.join(Review, Review.report_id == Report.id).where(Review.decision == status)

    reports = db.execute(stmt.limit(limit)).scalars().all()

    out: list[ReportDetailOut] = []
    for report in reports:
        review = report.reviews[-1] if report.reviews else None
        review_status = review.decision if review else "pending"
        if status and review_status != status:
            continue
        out.append(
            ReportDetailOut(
                **ReportOut.model_validate(report).model_dump(),
                analysis=report.analysis,
                review=review,
                review_status=review_status,
                similar_reports=[],
            )
        )
    return out


@router.get("/counts", summary="Quick report counts (nav badges / review queue)")
def report_counts(db: Session = Depends(get_db)):
    """Lightweight aggregate counts used for the HSE Review badge and the
    reviewer workspace: how many reports still need an HSE decision, how many
    were verified/rejected, and how many failed analysis."""
    total = db.scalar(select(func.count()).select_from(Report)) or 0
    analyzed = Report.processing_status == "analyzed"
    unreviewed = ~exists().where(Review.report_id == Report.id)
    pending = (
        db.scalar(select(func.count()).select_from(Report).where(analyzed, unreviewed)) or 0
    )
    verified = (
        db.scalar(
            select(func.count(func.distinct(Report.id)))
            .select_from(Report)
            .join(Review, Review.report_id == Report.id)
            .where(Review.decision.in_(["confirmed", "reviewed", "edited"]))
        )
        or 0
    )
    rejected = (
        db.scalar(
            select(func.count(func.distinct(Report.id)))
            .select_from(Report)
            .join(Review, Review.report_id == Report.id)
            .where(Review.decision == "rejected")
        )
        or 0
    )
    failed = (
        db.scalar(
            select(func.count()).select_from(Report).where(Report.processing_status == "failed")
        )
        or 0
    )
    return {
        "total": total,
        "pending": pending,
        "verified": verified,
        "rejected": rejected,
        "failed": failed,
    }


@router.get("/{report_id}", response_model=ReportDetailOut, summary="Get one report with full analysis")
def get_report(report_id: int, db: Session = Depends(get_db)):
    return _load_detail(db, report_id)


@router.post("/{report_id}/reanalyze", response_model=ReportDetailOut, summary="Re-run the AI pipeline on a stored report (updates its analysis)")
def reanalyze_report(report_id: int, db: Session = Depends(get_db)):
    """Re-process an existing report with the current pipeline and update its
    stored analysis in place — the 'process -> update database' step of the
    real flow. Prior review records are removed because they referred to the
    superseded result; the report returns to a pending review state.
    """
    report = db.execute(
        select(Report)
        .options(selectinload(Report.analysis), selectinload(Report.reviews))
        .where(Report.id == report_id)
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    result = analyze_report(report.report_text, use_llm=True)

    analysis = report.analysis
    if analysis is None:
        analysis = Analysis(report_id=report.id)
        db.add(analysis)
    analysis.sif_potential = result["sif_potential"]
    analysis.confidence = result["confidence"]
    analysis.priority = result["priority"]
    analysis.hazard = result["hazard"]
    analysis.potential_consequence = result["potential_consequence"]
    analysis.barrier_failure = result["barrier_failure"]
    analysis.life_saving_rule = result["life_saving_rule"]
    analysis.activity = result["activity"]
    analysis.location = result.get("location")
    analysis.equipment = result.get("equipment")
    analysis.unsafe_type = result.get("unsafe_type")
    analysis.rule_conditions = result.get("rule_conditions")
    analysis.evidence = result["evidence"]
    analysis.explanation = result["explanation"]
    analysis.recommended_follow_up = result["recommended_follow_up"]
    analysis.summary = result.get("summary")
    analysis.suggested_actions = result.get("suggested_actions")
    analysis.languages = result.get("languages")
    analysis.uncertainty_note = result.get("uncertainty_note")
    analysis.model = result["model"]

    # Superseded reviews no longer apply to the fresh result.
    for old_review in list(report.reviews):
        db.delete(old_review)

    db.commit()
    return _load_detail(db, report.id)