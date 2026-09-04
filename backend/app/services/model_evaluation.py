"""Stratified 5-Fold Cross-Validation & Model Evaluation Engine.

Evaluates and compares NLP / ML models (Naive Bayes, Logistic Regression,
Linear SVM, and Rule Engine Baseline) over the SIF dataset using Stratified
5-Fold Cross Validation.
"""

from __future__ import annotations

import os
import re
import time
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import fbeta_score, make_scorer
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from app.services.analysis_pipeline import analyze_report


def clean_text(text: str) -> str:
    """Normalize safety report text and expand domain acronyms."""
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()

    abbreviations = {
        "loto": "lockout tagout",
        "ptw": "permit to work",
        "ppe": "personal protective equipment",
        "h2s": "hydrogen sulfide",
        "jsa": "job safety analysis",
        "jha": "job hazard analysis",
        "ba": "breathing apparatus",
    }

    for short, expanded in abbreviations.items():
        text = re.sub(rf"\b{short}\b", expanded, text)

    return text


def load_evaluation_data(csv_path: str | None = None) -> tuple[pd.Series, pd.Series, int, int]:
    """Load and preprocess the SIF evaluation dataset."""
    if not csv_path or not os.path.exists(csv_path):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        processed_train = os.path.join(repo_root, "data", "processed", "train.csv")
        if os.path.exists(processed_train):
            csv_path = processed_train
        else:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            csv_path = os.path.join(base_dir, "data", "oil_hsse_sif_dataset.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)

    # Allow flexible column names
    desc_col = None
    for col in ["description", "report_text", "text"]:
        if col in df.columns:
            desc_col = col
            break

    label_col = None
    for col in ["sif_potential", "expect_sif", "target", "label"]:
        if col in df.columns:
            label_col = col
            break

    if not desc_col or not label_col:
        raise ValueError(
            f"Dataset must contain text column (description/report_text) and label column (sif_potential/target). Found: {list(df.columns)}"
        )

    df = df.dropna(subset=[desc_col, label_col]).copy()
    df["clean_text"] = df[desc_col].apply(clean_text)

    # Filter very short texts
    df = df[df["clean_text"].str.len() >= 8]

    label_map = {
        "yes": 1,
        "no": 0,
        "true": 1,
        "false": 0,
        "1": 1,
        "0": 0,
        1: 1,
        0: 0,
        True: 1,
        False: 0,
    }

    df["target"] = df[label_col].astype(str).str.strip().str.lower().map(label_map)
    df = df.dropna(subset=["target"])
    df["target"] = df["target"].astype(int)

    # For fast API response (<1.5s), sample up to 300 balanced cases from the dataset
    if len(df) > 300:
        pos_mask = df["target"] == 1
        neg_mask = df["target"] == 0
        n_pos = min(150, pos_mask.sum())
        n_neg = min(150, neg_mask.sum())
        pos_sample = df[pos_mask].sample(n=n_pos, random_state=42)
        neg_sample = df[neg_mask].sample(n=n_neg, random_state=42)
        df = pd.concat([pos_sample, neg_sample]).sample(frac=1.0, random_state=42).reset_index(drop=True)

    class_counts = df["target"].value_counts().to_dict()
    sif_pos = class_counts.get(1, 0)
    non_sif = class_counts.get(0, 0)

    if len(class_counts) < 2:
        raise ValueError("Dataset requires both SIF-potential (Yes) and Non-SIF (No) examples.")

    if min(sif_pos, non_sif) < 5:
        raise ValueError("At least 5 examples per class are required for 5-fold cross-validation.")

    return df["clean_text"], df["target"], int(sif_pos), int(non_sif)


def make_pipeline(classifier):
    """Pipeline with TF-IDF inside to prevent cross-validation data leakage."""
    return Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                max_features=10000,
                sublinear_tf=True,
            ),
        ),
        ("classifier", classifier),
    ])


def evaluate_sif_models(csv_path: str | None = None, n_splits: int = 5) -> dict:
    """Run Stratified 5-Fold Cross Validation comparing models and producing per-fold details."""
    started_at = time.time()
    X, y, sif_pos, non_sif = load_evaluation_data(csv_path)

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    f2_scorer = make_scorer(fbeta_score, beta=2, pos_label=1)

    models = {
        "Multinomial Naive Bayes": make_pipeline(MultinomialNB(alpha=0.1)),
        "Logistic Regression": make_pipeline(
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
        ),
        "Linear SVM": make_pipeline(
            LinearSVC(class_weight="balanced", random_state=42)
        ),
    }

    X_arr = X.to_numpy()
    y_arr = y.to_numpy()

    model_results = []

    # 1. Evaluate ML Models with per-fold metrics
    for model_name, pipeline in models.items():
        fold_details = []
        precision_list, recall_list, f1_list, f2_list, acc_list = [], [], [], [], []

        for fold_idx, (train_idx, val_idx) in enumerate(cv.split(X_arr, y_arr), start=1):
            X_train, y_train = X_arr[train_idx], y_arr[train_idx]
            X_val, y_val = X_arr[val_idx], y_arr[val_idx]

            pipeline.fit(X_train, y_train)
            y_pred = pipeline.predict(X_val)

            tp = int(np.sum((y_val == 1) & (y_pred == 1)))
            fp = int(np.sum((y_val == 0) & (y_pred == 1)))
            fn = int(np.sum((y_val == 1) & (y_pred == 0)))
            tn = int(np.sum((y_val == 0) & (y_pred == 0)))

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            f2 = (1 + 2**2) * prec * rec / (2**2 * prec + rec) if (2**2 * prec + rec) > 0 else 0.0
            acc = (tp + tn) / len(y_val) if len(y_val) > 0 else 0.0

            precision_list.append(prec)
            recall_list.append(rec)
            f1_list.append(f1)
            f2_list.append(f2)
            acc_list.append(acc)

            fold_details.append({
                "fold": fold_idx,
                "n_test": len(y_val),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "f2": round(f2, 4),
                "accuracy": round(acc, 4),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            })

        model_results.append({
            "model": model_name,
            "precision_mean": round(float(np.mean(precision_list)), 4),
            "precision_std": round(float(np.std(precision_list)), 4),
            "recall_mean": round(float(np.mean(recall_list)), 4),
            "recall_std": round(float(np.std(recall_list)), 4),
            "f1_mean": round(float(np.mean(f1_list)), 4),
            "f1_std": round(float(np.std(f1_list)), 4),
            "f2_mean": round(float(np.mean(f2_list)), 4),
            "f2_std": round(float(np.std(f2_list)), 4),
            "accuracy_mean": round(float(np.mean(acc_list)), 4),
            "accuracy_std": round(float(np.std(acc_list)), 4),
            "folds": fold_details,
        })

    # 2. Rule Engine Baseline Evaluation across the same 5 folds
    rule_fold_details = []
    r_prec_list, r_rec_list, r_f1_list, r_f2_list, r_acc_list = [], [], [], [], []

    rule_verdicts = np.array([
        1 if analyze_report(text, use_llm=False)["sif_potential"] else 0
        for text in X_arr
    ])

    for fold_idx, (train_idx, val_idx) in enumerate(cv.split(X_arr, y_arr), start=1):
        y_val = y_arr[val_idx]
        y_pred_rule = rule_verdicts[val_idx]

        tp = int(np.sum((y_val == 1) & (y_pred_rule == 1)))
        fp = int(np.sum((y_val == 0) & (y_pred_rule == 1)))
        fn = int(np.sum((y_val == 1) & (y_pred_rule == 0)))
        tn = int(np.sum((y_val == 0) & (y_pred_rule == 0)))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        f2 = (1 + 4) * prec * rec / (4 * prec + rec) if (4 * prec + rec) > 0 else 0.0
        acc = (tp + tn) / len(y_val) if len(y_val) > 0 else 0.0

        r_prec_list.append(prec)
        r_rec_list.append(rec)
        r_f1_list.append(f1)
        r_f2_list.append(f2)
        r_acc_list.append(acc)

        rule_fold_details.append({
            "fold": fold_idx,
            "n_test": len(y_val),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "f2": round(f2, 4),
            "accuracy": round(acc, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        })

    model_results.append({
        "model": "Rule Engine Baseline",
        "precision_mean": round(float(np.mean(r_prec_list)), 4),
        "precision_std": round(float(np.std(r_prec_list)), 4),
        "recall_mean": round(float(np.mean(r_rec_list)), 4),
        "recall_std": round(float(np.std(r_rec_list)), 4),
        "f1_mean": round(float(np.mean(r_f1_list)), 4),
        "f1_std": round(float(np.std(r_f1_list)), 4),
        "f2_mean": round(float(np.mean(r_f2_list)), 4),
        "f2_std": round(float(np.std(r_f2_list)), 4),
        "accuracy_mean": round(float(np.mean(r_acc_list)), 4),
        "accuracy_std": round(float(np.std(r_acc_list)), 4),
        "folds": rule_fold_details,
    })

    # Select best model (excluding rule baseline for pure ML choice, or comparing all)
    ml_models = [m for m in model_results if m["model"] != "Rule Engine Baseline"]
    best_model = sorted(
        ml_models,
        key=lambda item: (item["f2_mean"], item["recall_mean"]),
        reverse=True,
    )[0]

    # 3. Threshold Analysis for Logistic Regression
    lr_pipeline = make_pipeline(
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
    )
    lr_pipeline.fit(X_arr, y_arr)
    probs = lr_pipeline.predict_proba(X_arr)[:, 1]

    thresholds_analysis = []
    for thresh in [0.30, 0.40, 0.50, 0.60]:
        preds = (probs >= thresh).astype(int)
        tp = int(np.sum((y_arr == 1) & (preds == 1)))
        fp = int(np.sum((y_arr == 0) & (preds == 1)))
        fn = int(np.sum((y_arr == 1) & (preds == 0)))
        tn = int(np.sum((y_arr == 0) & (preds == 0)))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        f2 = 5 * prec * rec / (4 * prec + rec) if (4 * prec + rec) > 0 else 0.0

        thresholds_analysis.append({
            "threshold": thresh,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "f2": round(f2, 4),
            "reports_flagged_sif": int(tp + fp),
        })

    elapsed_ms = round((time.time() - started_at) * 1000)

    return {
        "evaluation_method": f"Stratified {n_splits}-fold cross-validation",
        "n_splits": n_splits,
        "total_records": len(y),
        "sif_positive_records": sif_pos,
        "non_sif_records": non_sif,
        "models": model_results,
        "recommended_model": best_model,
        "threshold_analysis": thresholds_analysis,
        "runtime_ms": elapsed_ms,
        "selection_reason": (
            "Selected using highest F2 score, with SIF recall as tie-breaker. "
            "In safety-critical SIF precursor detection, F2 gives 4x weight to recall over precision "
            "because missing a genuine life-threatening precursor is vastly more severe than sending an extra report for HSE review."
        ),
        "limitations": [
            "Validation metrics are computed over synthetic OIL-style safety reports.",
            "Must be validated on OIL operational HSSE historical records before deployment.",
            "Cross-validation measures generalizability across dataset folds; regular audit monitoring is recommended post-deployment.",
        ],
    }
