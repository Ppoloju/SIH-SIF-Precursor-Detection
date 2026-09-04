"""Real-world ML training discipline and cross-validation on the TRAINING set.

This module is the "learning / validation / testing" layer that makes the
project implementable in production. It is backend-only: the frontend never
renders these numbers (per product decision), but the machinery runs and its
outputs are stored in ``data/processed/reports/`` and served by the API.

Discipline enforced here (no leakage, no overfitting):

  * Only the TRAINING split is ever used for fitting or model selection.
  * The VALIDATION split is never touched during training or tuning.
  * The TEST split is evaluated exactly once by ``evaluate_test_once`` —
    nothing is fit or tuned on it.
  * TF-IDF is fitted inside every cross-validation fold (pipeline), so text
    statistics never leak from held-out rows.
  * Hyperparameters are chosen by NESTED cross-validation on the training set
    (inner grid search), not by peeking at validation/test.

Cross-validation methods available (all on the training set):

  * ``stratified_kfold``     — standard stratified k-fold
  * ``repeated_stratified``  — repeated k-fold for variance / confidence
  * ``leave_one_out``        — for small datasets (sampled if huge)
  * ``grouped``              — folds never split an incident_id group
                              (anti-leakage: fragments of one event stay
                              together)
  * ``nested``               — inner grid-search CV chooses hyperparameters,
                               outer CV gives the honest generalization score
  * ``learning_curve``       — score vs training size; train-vs-CV gap tells
                               underfitting (both low) from overfitting
                               (train high, CV low)
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import (
    GridSearchCV,
    GroupKFold,
    LeaveOneOut,
    StratifiedKFold,
    learning_curve,
)
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = DATA_DIR / "reports"
FALLBACK_CSV = ROOT / "backend" / "app" / "data" / "oil_hsse_sif_dataset.csv"

SEED = 42

_TOKEN_PATTERN = r"(?u)\b[A-Za-z]+(?:[a-z]{2,})?\b|[a-zA-Z]{2,}"


def _scores(y_true, y_pred) -> dict:
    return {
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
    }


def _agg(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows]
    mean = float(np.mean(vals))
    std = float(np.std(vals))
    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": round(float(min(vals)), 4),
        "max": round(float(max(vals)), 4),
        "ci95_low": round(mean - 1.96 * std / max(len(vals) ** 0.5, 1), 4),
        "ci95_high": round(mean + 1.96 * std / max(len(vals) ** 0.5, 1), 4),
    }


def _make_pipeline(classifier) -> Pipeline:
    """TF-IDF inside the pipeline => vectorizer fitted per-fold, no leakage."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=5000,
                    sublinear_tf=True,
                    token_pattern=_TOKEN_PATTERN,
                ),
            ),
            ("clf", classifier),
        ]
    )


# ---------------------------------------------------------------------------
# Data loading (TRAINING split only by default)
# ---------------------------------------------------------------------------

def load_training_data(
    train_csv: str | None = None,
    groups: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, dict]:
    """Load the training split as (texts, labels, group_ids, meta).

    Falls back to the bundled 500-report dataset when the real pipeline output
    is missing. group_ids are the incident ids from the canonical schema so
    grouped CV can guarantee no cross-split leakage of one incident.
    """
    path = Path(train_csv) if train_csv else DATA_DIR / "train.csv"
    if not path.exists():
        path = FALLBACK_CSV

    texts: list[str] = []
    labels: list[int] = []
    group_ids: list[str] = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            desc = (r.get("description") or r.get("report_text") or r.get("text") or "").strip()
            if len(desc) < 8:
                continue
            label = r.get("sif_potential") or r.get("target") or r.get("label")
            if label in ("1", "yes", "true", "True"):
                labels.append(1)
            elif label in ("0", "no", "false", "False"):
                labels.append(0)
            else:
                continue
            texts.append(desc)
            group_ids.append(r.get("incident_id") or r.get("report_id") or f"row{len(texts)}")

    meta = {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "rows": len(texts),
        "sif_positive": sum(labels),
    }
    g = np.array(group_ids) if groups else None
    return np.array(texts), np.array(labels), g, meta


def load_test_data(test_csv: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """TEST split — read-only for the single final evaluation."""
    path = Path(test_csv) if test_csv else DATA_DIR / "test.csv"
    if not path.exists():
        return np.array([]), np.array([])
    texts, labels, _, _ = load_training_data(str(path), groups=False)
    return texts, labels


# ---------------------------------------------------------------------------
# CV methods
# ---------------------------------------------------------------------------

def stratified_kfold(n_splits: int = 5) -> dict:
    X, y, _, meta = load_training_data()
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    folds = []
    for i, (tr, te) in enumerate(skf.split(X, y), start=1):
        pipeline.fit(X[tr], y[tr])
        folds.append({"fold": i, "n": int(len(te)), **_scores(y[te], pipeline.predict(X[te]))})
    return {
        "method": "Stratified k-fold (Logistic Regression)",
        "description": "Standard stratified k-fold on the training split; class ratio preserved in every fold.",
        "n_splits": n_splits,
        "dataset": meta,
        "folds": folds,
        "aggregate": {k: _agg(folds, k) for k in ("precision", "recall", "f1", "accuracy")},
    }


def repeated_stratified(n_splits: int = 5, repeats: int = 3) -> dict:
    X, y, _, meta = load_training_data()
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    all_folds = []
    for rep in range(repeats):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED + rep)
        for i, (tr, te) in enumerate(skf.split(X, y), start=1):
            pipeline.fit(X[tr], y[tr])
            all_folds.append({"repeat": rep + 1, "fold": i, **_scores(y[te], pipeline.predict(X[te]))})
    return {
        "method": f"Repeated stratified {n_splits}-fold x {repeats}",
        "description": "Repeats with different shuffles to estimate variance and a 95% confidence interval.",
        "n_splits": n_splits,
        "repeats": repeats,
        "dataset": meta,
        "folds": all_folds,
        "aggregate": {k: _agg(all_folds, k) for k in ("precision", "recall", "f1", "accuracy")},
    }


def leave_one_out(max_rows: int = 300) -> dict:
    X, y, _, meta = load_training_data()
    if len(X) > max_rows:
        rng = np.random.RandomState(SEED)
        idx = rng.choice(len(X), max_rows, replace=False)
        X, y = X[idx], y[idx]
        note = f"sampled to {max_rows} rows (LOO is O(n) fits)"
    else:
        note = "full dataset"
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    loo = LeaveOneOut()
    y_true, y_pred = [], []
    for tr, te in loo.split(X, y):
        pipeline.fit(X[tr], y[tr])
        y_true.append(y[te][0])
        y_pred.append(pipeline.predict(X[te])[0])
    return {
        "method": "Leave-one-out",
        "description": f"One held-out row per fit — lowest bias, highest variance; {note}.",
        "dataset": {**meta, "rows_used": int(len(X))},
        "folds": [{"fold": "all", "n": int(len(y_true)), **_scores(np.array(y_true), np.array(y_pred))}],
        "aggregate": {k: _agg([_scores(np.array(y_true), np.array(y_pred))], k)
                      for k in ("precision", "recall", "f1", "accuracy")},
    }


def grouped(n_splits: int = 5) -> dict:
    X, y, groups, meta = load_training_data(groups=True)
    gkf = GroupKFold(n_splits=n_splits)
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    folds = []
    for i, (tr, te) in enumerate(gkf.split(X, y, groups), start=1):
        pipeline.fit(X[tr], y[tr])
        folds.append({
            "fold": i,
            "n": int(len(te)),
            "groups_train": int(len(set(groups[tr]))),
            "groups_test": int(len(set(groups[te]))),
            **_scores(y[te], pipeline.predict(X[te])),
        })
    return {
        "method": f"Grouped {n_splits}-fold (by incident_id)",
        "description": "Folds are whole incidents — fragments of one event can never leak across folds.",
        "n_splits": n_splits,
        "dataset": meta,
        "folds": folds,
        "aggregate": {k: _agg(folds, k) for k in ("precision", "recall", "f1", "accuracy")},
    }


def nested(outer_splits: int = 5, inner_splits: int = 3) -> dict:
    """Nested CV: inner grid search picks C on train folds; outer CV gives the
    honest generalization score. The model NEVER sees validation/test."""
    X, y, _, meta = load_training_data()
    base = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2), min_df=2, max_features=5000,
                    sublinear_tf=True, token_pattern=_TOKEN_PATTERN,
                ),
            ),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
        ]
    )
    param_grid = {"clf__C": [0.1, 1.0, 10.0]}

    outer = StratifiedKFold(n_splits=outer_splits, shuffle=True, random_state=SEED)
    folds = []
    for i, (tr, te) in enumerate(outer.split(X, y), start=1):
        inner = GridSearchCV(base, param_grid, cv=inner_splits, scoring="f1",
                             n_jobs=-1, refit=True)
        inner.fit(X[tr], y[tr])
        folds.append({
            "fold": i,
            "n": int(len(te)),
            "best_C": float(inner.best_params_["clf__C"]),
            "inner_cv_f1": round(float(inner.best_score_), 4),
            **_scores(y[te], inner.predict(X[te])),
        })
    return {
        "method": f"Nested CV (outer {outer_splits}-fold, inner {inner_splits}-fold grid search)",
        "description": "Hyperparameters selected on training folds only via inner CV; outer folds give an unbiased generalization estimate. This is the anti-overfitting gold standard.",
        "param_grid": param_grid,
        "n_splits": outer_splits,
        "dataset": meta,
        "folds": folds,
        "aggregate": {k: _agg(folds, k) for k in ("precision", "recall", "f1", "accuracy")},
    }


def learning_curve_method(n_splits: int = 5, train_sizes: list[float] | None = None) -> dict:
    """Learning curve: score vs training size + train-vs-CV gap.

    Diagnosis:
      * train and CV both low  -> underfitting (model too simple / features weak)
      * train high, CV low     -> overfitting (model memorises training rows)
      * both high and close    -> healthy fit
    """
    X, y, _, meta = load_training_data()
    sizes = train_sizes or [0.1, 0.3, 0.6, 1.0]
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    sizes_, train_scores, test_scores = learning_curve(
        pipeline, X, y, cv=StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED),
        train_sizes=sizes, scoring="f1", n_jobs=-1,
    )
    points = []
    for i, size in enumerate(sizes_):
        train_mean = float(np.mean(train_scores[i]))
        cv_mean = float(np.mean(test_scores[i]))
        points.append({
            "train_rows": int(size),
            "fraction": round(size / len(X), 3),
            "train_f1": round(train_mean, 4),
            "cv_f1": round(cv_mean, 4),
            "gap": round(train_mean - cv_mean, 4),
        })
    final = points[-1]
    rising = len(points) >= 2 and points[-1]["cv_f1"] > points[-2]["cv_f1"] + 0.005
    if final["gap"] > 0.12:
        base = (
            f"Overfitting signal: training F1 ({final['train_f1']:.3f}) is "
            f"{final['gap']:.3f} above CV F1 ({final['cv_f1']:.3f}). "
        )
        if rising:
            base += ("The CV curve is still rising at the maximum training size — "
                     "more training data and/or stronger regularization should help.")
        else:
            base += "Reduce model capacity or increase regularization."
        diagnosis = base
    elif final["train_f1"] < 0.6 and final["cv_f1"] < 0.6:
        diagnosis = "Underfitting signal: both training and CV F1 are low; the features/model cannot capture the signal."
    else:
        diagnosis = "Healthy: training and CV F1 are close; the model generalises without memorising."
    return {
        "method": "Learning curve",
        "description": "F1 vs training-set size with a train-vs-CV gap used to detect under/overfitting.",
        "dataset": meta,
        "points": points,
        "diagnosis": diagnosis,
    }


# ---------------------------------------------------------------------------
# Full discipline report + single test evaluation
# ---------------------------------------------------------------------------

def run_training_report(n_splits: int = 5, repeats: int = 3) -> dict:
    """Run every CV method on the training split (validation/test untouched)."""
    started = time.time()
    X, y, _, meta = load_training_data()
    results = {
        "stratified_kfold": stratified_kfold(n_splits),
        "repeated_stratified": repeated_stratified(n_splits, repeats),
        "leave_one_out": leave_one_out(),
        "grouped": grouped(n_splits),
        "nested": nested(n_splits, max(2, n_splits - 2)),
        "learning_curve": learning_curve_method(n_splits),
    }
    # final fitted-on-train model metrics (validation untouched)
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    pipeline.fit(X, y)
    train_final = {
        "model": "Logistic Regression (TF-IDF)",
        "rows": int(len(X)),
        "train_f1": round(float(f1_score(y, pipeline.predict(X), zero_division=0)), 4),
        "note": "Fit on the training split only. Validation/test are never used for fitting.",
    }
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "discipline": {
            "learns_from": "training split only",
            "validation_used_for": "nothing in this report (reserved for final model confirmation)",
            "test_used_for": "evaluate_test_once() — a single held-out evaluation",
            "leakage_controls": [
                "TF-IDF fitted inside every fold (pipeline)",
                "Grouped folds by incident_id",
                "Nested CV for hyperparameters",
            ],
        },
        "methods": results,
        "train_final": train_final,
        "runtime_ms": round((time.time() - started) * 1000),
    }


def evaluate_test_once(n_splits: int = 5) -> dict:
    """The single real-world final evaluation: fit on train, evaluate on test.

    Nothing about the test split influences fitting, hyperparameters, or
    thresholds. This is the number that would be reported to stakeholders.
    """
    X, y, _, meta = load_training_data()
    X_test, y_test = load_test_data()
    if len(X_test) == 0:
        return {"ok": False, "note": "No test split available (data/processed/test.csv missing).", "dataset": meta}
    pipeline = _make_pipeline(LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))
    pipeline.fit(X, y)
    y_pred = pipeline.predict(X_test)
    return {
        "ok": True,
        "discipline": "Model fit on TRAINING split only; evaluated ONCE on the untouched TEST split.",
        "train_rows": int(len(X)),
        "test_rows": int(len(X_test)),
        "test_sif_positive": int(sum(y_test)),
        **_scores(y_test, y_pred),
        "dataset": meta,
    }


def write_report_markdown() -> Path:
    """Persist the training report to data/processed/reports/training_report.md."""
    rep = run_training_report()
    lines = [
        "# ML training report (training split only)",
        "",
        f"Generated {rep['generated_at']} — backend-only; not displayed in the frontend.",
        "",
        "## Discipline",
        "",
    ]
    for k, v in rep["discipline"].items():
        lines.append(f"- **{k.replace('_', ' ')}:** {v}")
    lines.append("")
    for name, res in rep["methods"].items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(res.get("description", ""))
        lines.append("")
        if name == "learning_curve":
            lines.append("| train rows | fraction | train F1 | CV F1 | gap |")
            lines.append("|---|---|---|---|---|")
            for p in res["points"]:
                lines.append(f"| {p['train_rows']} | {p['fraction']} | {p['train_f1']} | {p['cv_f1']} | {p['gap']} |")
            lines.append("")
            lines.append(f"**Diagnosis:** {res['diagnosis']}")
        else:
            lines.append("| metric | mean | std | min | max | 95% CI |")
            lines.append("|---|---|---|---|---|---|")
            for metric, a in res["aggregate"].items():
                lines.append(
                    f"| {metric} | {a['mean']} | {a['std']} | {a['min']} | {a['max']} "
                    f"| [{a['ci95_low']}, {a['ci95_high']}] |"
                )
            lines.append("")
    test = evaluate_test_once()
    lines += ["## Final held-out test evaluation (one-shot)", ""]
    if test.get("ok"):
        lines.append(f"- test rows: **{test['test_rows']}** ({test['test_sif_positive']} SIF positive)")
        for k in ("precision", "recall", "f1", "accuracy"):
            lines.append(f"- {k}: **{test[k]}**")
        lines.append(f"- {test['discipline']}")
    else:
        lines.append(test.get("note", "not run"))
    lines.append("")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / "training_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out