"""Feedback & training API — the human-in-the-loop retraining loop.

HSE review decisions are stored as labeled examples (``feedback`` table).
This router exposes:

* ``GET  /api/feedback/summary`` — how many reviews/labels exist, latest run.
* ``POST /api/feedback/train``    — re-measure model-vs-human agreement and
  mine learned signals from disagreements (offline-style training run stored
  in ``training_runs``; signals then tune future analyses in-process).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.services import adaptive

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.get("/summary", summary="Reviewed-label counts + latest training run")
def summary(db: Session = Depends(get_db)):
    return adaptive.feedback_summary(db)


@router.post("/train", summary="Train on reviewed labels (agreement metrics + learned signals)")
def train(db: Session = Depends(get_db)):
    """Re-fit the decision signals from human-reviewed reports."""
    return adaptive.train(db)
