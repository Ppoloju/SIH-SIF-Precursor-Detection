"""Real-time ML layer: missing-field imputation + noise removal + predict.

A lightweight model is trained ONCE on the TRAINING split only
(``data/processed/train.csv``; falls back to the bundled 500-report dataset),
persisted with joblib under ``data/processed/models/`` and lazy-loaded into the
process so analysis/ingest can call it in real time.

What it does at analysis time (``refine``):

  * If the deterministic engine left a structured field empty (no
    ``life_saving_rule``, ``hazard``, ``activity``, ``equipment`` detected in
    the text), the trained model predicts it from the description and the
    value is filled in — flagged in ``uncertainty_note`` and the model tag so
    it is never mistaken for an engine extraction.
  * Non-empty engine values are NEVER overwritten (learn from existing fields,
    do not regenerate valid values).
  * The SIF verdict is never flipped by the model.

What it does for batch cleaning (``dedupe_descriptions`` / ``is_noise``):

  * Removes exact/near-duplicate reports (fingerprint + length filter) so
    noise and repeated rows do not reach analysis.

The model learns ONLY from the training data; validation and test splits are
never read by this module.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "processed"
MODELS_DIR = DATA_DIR / "models"
FALLBACK_CSV = ROOT / "backend" / "app" / "data" / "oil_hsse_sif_dataset.csv"

SEED = 42
MIN_DESC_LEN = 15
_TOKEN_PATTERN = r"(?u)\b[A-Za-z]+(?:[a-z]{2,})?\b|[a-zA-Z]{2,}"

# in-process singleton
_ACTIVE: dict = {"loaded": False, "meta": {}, "model": None}

_TOP_N = {"hazard": 25, "activity": 20, "equipment": 15}


def _fingerprint(text: str) -> str:
    return re.sub(r"[^a-z0-9\u0900-\u09ff]+", " ", text.lower()).strip()


# ---------------------------------------------------------------------------
# Training (training split only)
# ---------------------------------------------------------------------------

def _load_training_rows() -> list[dict]:
    path = DATA_DIR / "train.csv"
    if not path.exists():
        path = FALLBACK_CSV
    rows: list[dict] = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            desc = (r.get("description") or r.get("report_text") or r.get("text") or "").strip()
            if len(desc) < MIN_DESC_LEN:
                continue
            rows.append(r)
    return rows


def train_and_persist(force: bool = False) -> dict:
    """Fit + persist the imputation model from the training split only."""
    if _ACTIVE["loaded"] and not force:
        return _ACTIVE["meta"]

    rows = _load_training_rows()
    if not rows:
        raise FileNotFoundError("No training data found (data/processed/train.csv).")

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.pipeline import make_pipeline

    texts = [r["description"] for r in rows]
    vec = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_features=10000,
        sublinear_tf=True, token_pattern=_TOKEN_PATTERN,
    )
    X = vec.fit_transform(texts)

    def multiclass(field: str, top_n: int | None) -> tuple[object, list[str]]:
        values = [r.get(field) or "" for r in rows]
        counter: dict[str, int] = {}
        for v in values:
            counter[v] = counter.get(v, 0) + 1
        ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        if top_n is not None:
            ordered = ordered[:top_n]
        classes = [c for c, _ in ordered]
        y = np.array([classes.index(v) if v in classes else len(classes) for v in values])
        classes.append("__unknown__")
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
        clf.fit(X, y)
        return clf, classes

    def multilabel(field: str, top_n: int) -> tuple[object, list[str]]:
        terms: dict[str, int] = {}
        for r in rows:
            for item in re.split(r"[;,]", r.get(field) or ""):
                item = item.strip()
                if item:
                    terms[item] = terms.get(item, 0) + 1
        ordered = sorted(terms.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
        classes = [t for t, _ in ordered]
        Y = np.zeros((len(rows), len(classes)), dtype=int)
        for i, r in enumerate(rows):
            for item in re.split(r"[;,]", r.get(field) or ""):
                item = item.strip()
                if item in classes:
                    Y[i, classes.index(item)] = 1
        clf = OneVsRestClassifier(
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
        )
        clf.fit(X, Y)
        return clf, classes

    sif_y = np.array([1 if (r.get("sif_potential") or "0").strip() in ("1", "True", "true", "yes") else 0
                      for r in rows])
    sif_clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
    sif_clf.fit(X, sif_y)

    lsr_clf, lsr_classes = multiclass("lsr", None)
    hazard_clf, hazard_classes = multiclass("hazard", _TOP_N["hazard"])
    activity_clf, activity_classes = multiclass("activity", _TOP_N["activity"])
    equip_clf, equip_classes = multilabel("equipment", _TOP_N["equipment"])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import joblib
    except ImportError:  # pragma: no cover
        joblib = None
    payload = {
        "vectorizer": vec,
        "sif": sif_clf,
        "lsr": (lsr_clf, lsr_classes),
        "hazard": (hazard_clf, hazard_classes),
        "activity": (activity_clf, activity_classes),
        "equipment": (equip_clf, equip_classes),
    }
    model_path = MODELS_DIR / "sif_imputer.joblib"
    if joblib is not None:
        joblib.dump(payload, model_path)
    else:  # pragma: no cover — joblib ships with sklearn
        import pickle
        with open(model_path, "wb") as f:
            pickle.dump(payload, f)

    meta = {
        "loaded": True,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "train_rows": len(rows),
        "train_sif_positive": int(sif_y.sum()),
        "model_path": str(model_path.relative_to(ROOT)),
        "fields": {
            "sif": "binary probability",
            "lsr": {"classes": len(lsr_classes) - 1},
            "hazard": {"classes": len(hazard_classes) - 1},
            "activity": {"classes": len(activity_classes) - 1},
            "equipment": {"terms": len(equip_classes)},
        },
        "learns_from": "data/processed/train.csv (training split only; validation/test never read)",
    }
    (MODELS_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _ACTIVE.update({"loaded": True, "meta": meta, "model": payload})
    logger.info("ML imputation model trained on %d rows", len(rows))
    return meta


def _ensure_loaded() -> dict | None:
    if _ACTIVE["loaded"]:
        return _ACTIVE["model"]
    meta_path = MODELS_DIR / "meta.json"
    model_path = MODELS_DIR / "sif_imputer.joblib"
    if not meta_path.exists() or not model_path.exists():
        try:
            train_and_persist()
        except FileNotFoundError:
            return None
    try:
        import joblib
    except ImportError:  # pragma: no cover
        joblib = None
    if joblib is None:  # pragma: no cover
        import pickle
        with open(model_path, "rb") as f:
            payload = pickle.load(f)
    else:
        payload = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    _ACTIVE.update({"loaded": True, "meta": meta, "model": payload})
    return payload


def status() -> dict:
    """Model status — used by the API; not displayed in the frontend."""
    _ensure_loaded()
    return dict(_ACTIVE["meta"])


# ---------------------------------------------------------------------------
# Real-time inference
# ---------------------------------------------------------------------------

def predict(text: str) -> dict:
    """Predict canonical fields for one description (real-time)."""
    model = _ensure_loaded()
    if model is None:
        return {"available": False}
    if not text or not text.strip():
        return {"available": True, "error": "empty text"}
    vec = model["vectorizer"]
    X = vec.transform([text])
    sif_prob = float(model["sif"].predict_proba(X)[:, 1][0])
    lsr_clf, lsr_classes = model["lsr"]
    hazard_clf, hazard_classes = model["hazard"]
    activity_clf, activity_classes = model["activity"]
    equip_clf, equip_classes = model["equipment"]

    lsr = lsr_classes[int(lsr_clf.predict(X)[0])]
    hazard = hazard_classes[int(hazard_clf.predict(X)[0])]
    activity = activity_classes[int(activity_clf.predict(X)[0])]
    eq_mask = equip_clf.predict(X)[0]
    equipment = [c for c, keep in zip(equip_classes, eq_mask) if keep]

    return {
        "available": True,
        "sif_probability": round(sif_prob, 3),
        "sif_potential": bool(sif_prob >= 0.5),
        "lsr": None if lsr == "__unknown__" else lsr,
        "hazard": None if hazard == "__unknown__" else hazard,
        "activity": None if activity == "__unknown__" else activity,
        "equipment": equipment,
        "note": "Predicted by the trained model (training split only).",
    }


def refine(result: dict, text: str) -> dict:
    """Fill MISSING structured fields of an engine result with model predictions.

    Conservative by design:
      * non-empty engine values are never overwritten,
      * the SIF verdict is never flipped,
      * every filled field is flagged in ``uncertainty_note`` and the model tag.
    """
    try:
        pred = predict(text)
    except Exception:  # never break analysis because of the ML layer
        return result
    if not pred.get("available"):
        return result

    filled: list[str] = []
    if not result.get("life_saving_rule") and pred.get("lsr"):
        result["life_saving_rule"] = pred["lsr"]
        filled.append(f"life-saving rule '{pred['lsr']}'")
    if not result.get("hazard") and pred.get("hazard"):
        result["hazard"] = pred["hazard"]
        filled.append(f"hazard '{pred['hazard']}'")
    if not result.get("activity") and pred.get("activity"):
        result["activity"] = pred["activity"]
        filled.append(f"activity '{pred['activity']}'")
    if not result.get("equipment") and pred.get("equipment"):
        result["equipment"] = pred["equipment"]
        filled.append(f"equipment ({', '.join(pred['equipment'][:4])})")

    if not filled:
        return result

    note = (
        "Field(s) not stated explicitly in the report were predicted by the "
        "trained model from similar training incidents: " + "; ".join(filled) + ". "
        "Requires HSE confirmation."
    )
    existing = result.get("uncertainty_note")
    result["uncertainty_note"] = f"{note} ({existing})" if existing else note
    model = result.get("model") or "rules-v1"
    if "+ml" not in model:
        result["model"] = f"{model}+ml"
    return result


# ---------------------------------------------------------------------------
# Noise removal (batch + single)
# ---------------------------------------------------------------------------

def is_noise(description: str) -> bool:
    """A description is noise when it is too short to carry a signal."""
    desc = (description or "").strip()
    if len(desc) < MIN_DESC_LEN:
        return True
    # junk: no letters at all (pure symbols/numbers)
    if not re.search(r"[A-Za-z\u0900-\u09ff]", desc):
        return True
    return False


def dedupe_descriptions(rows: list[dict], keep: str = "description") -> tuple[list[dict], list[dict]]:
    """Remove exact/near-duplicate rows by normalized fingerprint.

    Returns (clean_rows, duplicate_rows). The first occurrence (by list order)
    is kept.
    """
    seen: set[str] = set()
    clean: list[dict] = []
    dups: list[dict] = []
    for row in rows:
        fp = _fingerprint(row.get(keep) or "")
        if not fp or fp in seen:
            dups.append(row)
            continue
        seen.add(fp)
        clean.append(row)
    return clean, dups