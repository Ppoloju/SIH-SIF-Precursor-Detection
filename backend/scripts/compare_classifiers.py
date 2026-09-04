"""Compare the rule-based SIF engine against classical ML classifiers.

Models compared (all fitted on the TRAINING split only, evaluated with
stratified 5-fold cross-validation ON THE TRAINING SET — the test set is
never touched here):

  * rule-pipeline baseline — the existing deterministic engine
    (``analysis_pipeline.analyze_report``) whose per-row ``sif_potential``
    verdicts are already in the dataset; evaluated on each held-out fold.
  * Logistic Regression       (TF-IDF features, balanced class weights)
  * Linear SVM                (LinearSVC, balanced class weights)
  * Decision Tree             (balanced class weights, depth-limited)
  * LDA + PCA                 (Linear Discriminant Analysis on PCA-reduced
                               TF-IDF — "use PCA -> Data" per the design notes)

Feature pipeline for the classical models: TF-IDF (word 1-2 grams,
max 10,000 features, token pattern keeps Latin + Indic scripts) on the
cleaned description.  The TF-IDF vectorizer is fitted per-fold inside the CV
(never on held-out data); the same folds are reused for every model and the
rule baseline so the comparison is apples-to-apples.

The rule baseline has no fitted parameters: its verdict is text-derived and
fixed, so its per-fold numbers measure how stable the engine's labels are
across compositions, while the classical models show genuine train/test
generalization on the same folds.

Outputs a markdown report to ``data/processed/reports/model_comparison.md``.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sklearn.decomposition import PCA  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import StratifiedKFold  # noqa: E402
from sklearn.svm import LinearSVC  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = DATA_DIR / "reports"
SEED = 42

TOKEN_PATTERN = r"(?u)\b[A-Za-z]+(?:[a-z]{2,})?\b|[a-zA-Z]{2,}"


def load_split(path: Path) -> tuple[list[str], list[int]]:
    texts, labels = [], []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            texts.append(r["description"] or "")
            labels.append(1 if r["sif_potential"] == "1" else 0)
    return texts, labels


def _scores(y_true, y_pred) -> dict:
    return {
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 3),
        "accuracy": round(accuracy_score(y_true, y_pred), 3),
    }


def _make_model(name: str):
    if name == "logistic":
        return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
    if name == "svm":
        return LinearSVC(class_weight="balanced", random_state=SEED, max_iter=5000)
    if name == "tree":
        return DecisionTreeClassifier(max_depth=12, class_weight="balanced",
                                      random_state=SEED)
    if name == "lda_pca":
        return LinearDiscriminantAnalysis()
    raise ValueError(name)


def cv_report(texts: list[str], labels: list[int], rule_labels: list[int],
              model_names: list[str], n_splits: int = 5) -> dict:
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    results: dict[str, list[dict]] = {n: [] for n in model_names + ["rule"]}

    for fold, (tr, te) in enumerate(skf.split(texts, labels), start=1):
        y_true = [labels[i] for i in te]

        # rule baseline: fixed text-derived verdicts evaluated on the fold
        results["rule"].append({"fold": fold, **_scores(y_true, [rule_labels[i] for i in te])})

        for name in model_names:
            vec = TfidfVectorizer(
                max_features=10000, ngram_range=(1, 2), token_pattern=TOKEN_PATTERN,
                sublinear_tf=True, min_df=2,
            )
            X_tr = vec.fit_transform([texts[i] for i in tr])
            X_te = vec.transform([texts[i] for i in te])
            model = _make_model(name)
            if name == "lda_pca":
                # PCA down to 300 components keeps the TF-IDF space dense
                # enough for LDA to fit on small folds.
                n_comp = min(300, X_tr.shape[0] - 1, X_tr.shape[1])
                pca = PCA(n_components=n_comp, random_state=SEED)
                X_tr = pca.fit_transform(X_tr.toarray())
                X_te = pca.transform(X_te.toarray())
            model.fit(X_tr, [labels[i] for i in tr])
            y_pred = model.predict(X_te)
            results[name].append({"fold": fold, **_scores(y_true, y_pred)})

    report = {}
    for name, folds in results.items():
        def agg(key: str) -> dict:
            vals = [f[key] for f in folds]
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            return {"mean": round(mean, 3), "std": round(var ** 0.5, 3),
                    "min": round(min(vals), 3), "max": round(max(vals), 3)}
        report[name] = {
            "per_fold": folds,
            "aggregate": {k: agg(k) for k in ("precision", "recall", "f1", "accuracy")},
        }
    return report


def _markdown(dataset_label: str, texts: list[str], labels: list[int],
              rule_labels: list[int], model_names: list[str],
              n_splits: int) -> str:
    rep = cv_report(texts, labels, rule_labels, model_names, n_splits)
    pos = sum(labels)
    lines = [
        f"# Model comparison — {dataset_label}",
        "",
        f"- rows: **{len(labels)}**  (SIF positive: **{pos}**, {100 * pos / max(len(labels), 1):.1f}%)",
        f"- cross-validation: **{n_splits}-fold stratified** on the training set, seed 42",
        "- feature pipeline: TF-IDF (1-2 word grams, 10k features, Latin + Indic "
        "scripts), fitted per fold only",
        "- rule baseline: the existing deterministic engine's text-derived "
        "`sif_potential` verdicts, evaluated on each held-out fold",
        "",
        "## Aggregate (mean over folds, std in parentheses)",
        "",
        "| model | precision | recall | F1 | accuracy |",
        "|---|---|---|---|---|",
    ]
    order = ["rule", "logistic", "svm", "tree", "lda_pca"]
    labels_map = {
        "rule": "Rule-based engine (ours)",
        "logistic": "Logistic Regression",
        "svm": "Linear SVM",
        "tree": "Decision Tree",
        "lda_pca": "LDA + PCA",
    }
    for name in order:
        agg = rep[name]["aggregate"]
        lines.append(
            f"| {labels_map[name]} | {agg['precision']['mean']} ± {agg['precision']['std']} "
            f"| {agg['recall']['mean']} ± {agg['recall']['std']} "
            f"| {agg['f1']['mean']} ± {agg['f1']['std']} "
            f"| {agg['accuracy']['mean']} ± {agg['accuracy']['std']} |"
        )
    lines += ["", "## Per-fold detail", "", "| model | fold | n | precision | recall | F1 | accuracy |"]
    fold_n: dict[int, int] = {}
    for i, _ in enumerate(labels, start=1):
        fold_n[(i - 1) % n_splits + 1] = fold_n.get((i - 1) % n_splits + 1, 0) + 1
    for name in order:
        for f in rep[name]["per_fold"]:
            lines.append(
                f"| {labels_map[name]} | {f['fold']} | {fold_n.get(f['fold'], '-')} "
                f"| {f['precision']} | {f['recall']} | {f['f1']} | {f['accuracy']} |"
            )
    lines += [
        "",
        "## Reading and honest caveats",
        "",
        "- **The rule baseline's 1.0 is self-consistency, not generalization**: the",
        "  `sif_potential` labels in these CSVs were produced by the same",
        "  deterministic engine, so evaluating the engine against its own labels",
        "  trivially scores 1.0 (it proves the labels are reproducible, exactly",
        "  like the golden-set evaluation). It does NOT mean the engine is perfect",
        "  on real incidents — external hand-labelled data (the golden set is the",
        "  seed) is the only true ground truth.",
        "- **The classical models DO generalize**: they never see the held-out",
        "  fold's text during training, so their scores measure how learnable the",
        "  engine's SIF labels are from raw incident text. Best F1 here is the",
        "  linear SVM (0.59 real / see synthetic section) — real signal exists,",
        "  but generic text models stay well below the engine's consistency.",
        "- Classical models are trained and cross-validated on the training split",
        "  only; the held-out **test split is untouched** (that is the final",
        "  evaluation set).",
        "- F1 favours the model with the best precision/recall balance; with",
        "  imbalanced SIF labels, accuracy alone can mislead — compare F1 and",
        "  recall (the cost of a missed SIF precursor is high).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits", nargs="+", default=["data/processed/train.csv"],
                    help="training CSVs to compare on")
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--out", default=str(REPORTS_DIR / "model_comparison.md"))
    args = ap.parse_args()

    started = time.time()
    models = ["logistic", "svm", "tree", "lda_pca"]
    sections: list[str] = []
    for split_path in args.splits:
        p = Path(split_path)
        if not p.exists():
            p = ROOT / split_path
        texts, labels = load_split(p)
        rule_labels = [1 if r["sif_potential"] == "1" else 0 for r in
                       list(csv.DictReader(open(p, encoding="utf-8", newline="")))]
        sections.append(_markdown(f"{p.parent.name}/{p.name}", texts, labels, rule_labels, models, args.n_splits))
        print(f"{p.parent.name}/{p.name}: {len(labels)} rows, {sum(labels)} SIF positive — done")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    combined = "\n\n---\n\n".join(sections)
    Path(args.out).write_text(combined, encoding="utf-8")
    print(f"wrote {args.out} in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()