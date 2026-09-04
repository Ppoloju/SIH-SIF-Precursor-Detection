"""Run the golden-set evaluation and print a terminal report.

Usage:
    python scripts/evaluate.py           # compact table
    python scripts/evaluate.py --cv 5    # + stratified k-fold stability
    python scripts/evaluate.py --json    # full JSON (for docs / CI)
"""

from __future__ import annotations

import json
import sys

if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.path.insert(0, "..")

from app.services.evaluation import run_evaluation, run_kfold_cv  # noqa: E402


def _cv_flag() -> int | None:
    """Parse ``--cv`` / ``--cv 5``; bare ``--cv`` defaults to 5 folds."""
    if "--cv" not in sys.argv:
        return None
    i = sys.argv.index("--cv")
    if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
        return int(sys.argv[i + 1])
    return 5


def _row(rule: dict) -> str:
    return (
        f"  {rule['rule']:<26} sup {rule['support']:>2} | "
        f"TP {rule['tp']:>2}  FP {rule['fp']:>2}  FN {rule['fn']:>2} | "
        f"P {rule['precision']:.2f}  R {rule['recall']:.2f}  F1 {rule['f1']:.2f}"
    )


def _print_cv(cv: dict) -> None:
    print("-" * 72)
    print(f"Stratified {cv['k']}-fold stability  ({cv['n_cases']} golden cases)")
    print(f"  {'fold':<5}{'n':>4}{'SIF+':>6}  P      R      F1     acc")
    for f in cv["folds"]:
        print(f"  {f['fold']:<5}{f['n']:>4}{f['sif_positive']:>6}  "
              f"{f['precision']:.3f}  {f['recall']:.3f}  {f['f1']:.3f}  {f['accuracy']:.3f}   "
              f"({f['languages']})")
    a = cv["aggregate"]
    print(f"  mean±std  F1 {a['f1']['mean']:.3f}±{a['f1']['std']:.3f}  "
          f"P {a['precision']['mean']:.3f}±{a['precision']['std']:.3f}  "
          f"R {a['recall']['mean']:.3f}±{a['recall']['std']:.3f}  "
          f"acc {a['accuracy']['mean']:.3f}±{a['accuracy']['std']:.3f}")
    print(f"  F1 range {a['f1']['min']:.3f}–{a['f1']['max']:.3f}  "
          f"95% CI [{a['f1']['ci95_low']:.3f}, {a['f1']['ci95_high']:.3f}]")
    print("  " + cv["methodology"][:110] + "…")


def main() -> None:
    k = _cv_flag()
    payload: dict = {"evaluation": run_evaluation()}
    if k is not None:
        payload["cross_validation"] = run_kfold_cv(k)
    if "--json" in sys.argv:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    r = payload["evaluation"]
    s = r["sif_classification"]
    print("=" * 72)
    print("SIH SIF Precursor Detection — golden-set evaluation")
    print(r["dataset"]["name"])
    print("=" * 72)
    print(f"SIF classification   precision {s['precision']:.3f}  recall {s['recall']:.3f}  "
          f"F1 {s['f1']:.3f}  accuracy {s['accuracy']:.3f}")
    print(f"                     TP {s['tp']}  FP {s['fp']}  FN {s['fn']}  TN {s['tn']}")
    print("-" * 72)
    print("Life-Saving-Rule mapping (multi-label)")
    for rule in r["rules"]:
        print(_row(rule))
    print("-" * 72)
    ml = r["multilingual"]
    print(f"Multilingual cases   {ml['cases']}  SIF-correct {ml['sif_correct']} "
          f"({ml['sif_accuracy']}%)  — Hindi/Bengali/Assamese")
    langs = ", ".join(f"{l['lang']}: {l['cases']}" for l in r["languages"])
    print(f"By language          {langs}")
    print(f"Runtime              {r['runtime_ms']} ms  (deterministic, no LLM)")
    print("Methodology          " + r["methodology"][:120])
    if k is not None:
        _print_cv(payload["cross_validation"])
    print("=" * 72)


if __name__ == "__main__":
    main()
