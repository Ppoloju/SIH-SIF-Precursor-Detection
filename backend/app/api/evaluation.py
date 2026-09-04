"""Evaluation & ML API — backend functionality (not rendered in the frontend).

The frontend deliberately does NOT display model evaluation; these endpoints
keep the machinery working so training, cross-validation and real-time
inference happen server-side:

  * ``GET  /api/evaluation``        — golden-set metrics (kept for tooling)
  * ``GET|POST /api/model/evaluate`` — cross-validation methods on the
                                       TRAINING split (method=..., n_splits=...)
  * ``GET  /api/model/status``       — trained model status
  * ``POST /api/model/predict``      — real-time prediction / field imputation
"""

import time

from fastapi import APIRouter, Body, Query

from app.services.evaluation import run_evaluation, run_kfold_cv
from app.services import ml_inference, ml_training
from app.services.model_evaluation import evaluate_sif_models

router = APIRouter(tags=["evaluation"])

_cache: dict = {"at": 0.0, "payload": None}
_TTL_SECONDS = 300.0


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


_METHODS = {
    "stratified_kfold": ml_training.stratified_kfold,
    "repeated_stratified": ml_training.repeated_stratified,
    "leave_one_out": ml_training.leave_one_out,
    "grouped": ml_training.grouped,
    "nested": ml_training.nested,
    "learning_curve": ml_training.learning_curve_method,
}


@router.post("/api/model/evaluate", summary="Run cross-validation on the TRAINING split")
@router.get("/api/model/evaluate", summary="Run cross-validation on the TRAINING split")
def evaluate_model_endpoint(
    method: str = Query(default="all", description="stratified_kfold | repeated_stratified | leave_one_out | grouped | nested | learning_curve | all"),
    n_splits: int = Query(default=5, ge=2, le=20),
    repeats: int = Query(default=3, ge=1, le=10),
):
    try:
        if method == "all":
            report = ml_training.run_training_report(n_splits=n_splits, repeats=repeats)
            return {"success": True, "data": report}
        if method not in _METHODS:
            return {"success": False, "error": f"unknown method '{method}' — choose from {sorted(_METHODS)}"}
        fn = _METHODS[method]
        if method == "repeated_stratified":
            data = fn(n_splits=n_splits, repeats=repeats)
        else:
            data = fn(n_splits=n_splits)
        return {"success": True, "data": data}
    except Exception as error:  # noqa: BLE001
        return {"success": False, "error": str(error)}


@router.get("/api/model/status", summary="Trained ML model status")
def model_status():
    try:
        return {"success": True, "data": ml_inference.status()}
    except Exception as error:  # noqa: BLE001
        return {"success": False, "error": str(error)}


@router.post("/api/model/predict", summary="Real-time prediction / missing-field imputation")
def model_predict(text: str = Body(..., embed=True)):
    try:
        return {"success": True, "data": ml_inference.predict(text)}
    except Exception as error:  # noqa: BLE001
        return {"success": False, "error": str(error)}


@router.post("/api/model/train", summary="(Re)train the real-time imputation model on the training split")
def model_train():
    try:
        meta = ml_inference.train_and_persist(force=True)
        return {"success": True, "data": meta}
    except Exception as error:  # noqa: BLE001
        return {"success": False, "error": str(error)}