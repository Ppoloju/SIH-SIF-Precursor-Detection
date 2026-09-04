"""Evaluation API — golden-set metrics for the frontend Evaluation page."""

import time

from fastapi import APIRouter, Query

from app.services.evaluation import run_evaluation, run_kfold_cv

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

# Deterministic result; recomputing takes < 1s so a tiny TTL cache keeps the
# page snappy while still being honest if the engine code changes.
_cache: dict = {"at": 0.0, "payload": None}
_TTL_SECONDS = 30.0


@router.get("", summary="Golden-set SIF detection & Life-Saving-Rule metrics")
def evaluation(fresh: bool = Query(default=False, description="Force recompute")):
    now = time.time()
    if fresh or _cache["payload"] is None or now - _cache["at"] > _TTL_SECONDS:
        _cache["at"] = now
        base = run_evaluation()
        # Stratified 5-fold stability over the same golden set (~30 ms extra,
        # cached with the rest).
        base["cross_validation"] = run_kfold_cv(5)
        _cache["at"] = now
        _cache["payload"] = base
    payload = dict(_cache["payload"])
    payload["cached"] = now - _cache["at"] < _TTL_SECONDS
    return payload
