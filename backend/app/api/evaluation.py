"""Evaluation API — golden-set metrics for the frontend Evaluation page."""

import time

from fastapi import APIRouter, Query

from app.services.evaluation import run_evaluation, run_kfold_cv
from app.services.model_evaluation import evaluate_sif_models

router = APIRouter(tags=["evaluation"])

# Deterministic result; recomputing takes < 1s so a tiny TTL cache keeps the
# page snappy while still being honest if the engine code changes.
_cache: dict = {"at": 0.0, "payload": None}
_TTL_SECONDS = 30.0


@router.get("/api/evaluation", summary="Golden-set SIF detection & Life-Saving-Rule metrics")
def evaluation(fresh: bool = Query(default=False, description="Force recompute")):
    now = time.time()
    if fresh or _cache["payload"] is None or now - _cache["at"] > _TTL_SECONDS:
        _cache["at"] = now
        base = run_evaluation()
        base["cross_validation"] = run_kfold_cv(5)
        try:
            base["ml_cross_validation"] = evaluate_sif_models()
        except Exception:
            base["ml_cross_validation"] = None
        _cache["at"] = now
        _cache["payload"] = base
    payload = dict(_cache["payload"])
    payload["cached"] = now - _cache["at"] < _TTL_SECONDS
    return payload


@router.post("/api/model/evaluate", summary="Run Stratified 5-Fold ML Model Evaluation")
@router.get("/api/model/evaluate", summary="Run Stratified 5-Fold ML Model Evaluation")
def evaluate_model_endpoint():
    try:
        results = evaluate_sif_models()
        return {
            "success": True,
            "data": results,
        }
    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }
