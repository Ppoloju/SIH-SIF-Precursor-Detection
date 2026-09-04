"""HSE review API — human-in-the-loop validation of AI results."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.db import get_db
from app.models.entities import Report, Review
from app.schemas.reports import ReviewUpdate
from app.api.reports import _load_detail
from app.services import adaptive

router = APIRouter(prefix="/api/reports", tags=["review"])


def _human_sif_from_decision(decision: str | None, ai_sif: bool | None) -> bool | None:
    """Map a review decision to the SIF label used for training."""
    if decision == "confirmed":
        return True
    if decision == "rejected":
        return False
    if decision == "reviewed":
        return ai_sif  # accepted as-is => agreement
    return None  # 'edited' carries no explicit SIF stance


@router.patch("/{report_id}/review", response_model=dict, summary="Record an HSE review decision")
def review_report(
    report_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
):
    report = db.execute(
        select(Report)
        .options(selectinload(Report.analysis), selectinload(Report.reviews))
        .where(Report.id == report_id)
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    decision = payload.decision
    if payload.mark_reviewed and not decision:
        decision = "reviewed"

    review = Review(
        report_id=report.id,
        reviewer=payload.reviewer,
        decision=decision,
        corrected_priority=payload.corrected_priority,
        corrected_rule=payload.corrected_rule,
        comments=payload.comments,
        reviewed_at=datetime.utcnow(),
    )
    db.add(review)
    db.commit()

    # Human-in-the-loop: store the decision as a labeled training example.
    ai_sif = report.analysis.sif_potential if report.analysis else None
    feedback = adaptive.capture_feedback(
        db,
        report,
        decision=decision,
        reviewer=payload.reviewer,
        human_sif=_human_sif_from_decision(decision, ai_sif),
        human_rule=payload.corrected_rule,
        human_priority=payload.corrected_priority,
        comments=payload.comments,
    )

    detail = _load_detail(db, report_id)
    return {
        "ok": True,
        "report": detail,
        "decision": decision,
        "feedback_captured": True,
        "feedback_id": feedback.id,
    }