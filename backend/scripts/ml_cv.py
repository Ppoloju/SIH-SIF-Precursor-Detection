"""Run every cross-validation method + training discipline report.

Usage (from the backend directory):

    ./.venv/Scripts/python.exe scripts/ml_cv.py               # full report + markdown
    ./.venv/Scripts/python.exe scripts/ml_cv.py --method nested
    ./.venv/Scripts/python.exe scripts/ml_cv.py --json

All methods run on the TRAINING split only (data/processed/train.csv, with a
fallback to the bundled 500-report dataset). Validation and test splits are
never used for fitting; the test split is evaluated exactly once at the end.
The report is written to data/processed/reports/training_report.md (backend
only — it is not displayed in the frontend).
"""

from __future__ import annotations

import json
import sys

if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.path.insert(0, "..")

from app.services import ml_training  # noqa: E402


def main() -> None:
    method = None
    if "--method" in sys.argv:
        method = sys.argv[sys.argv.index("--method") + 1]

    print("=" * 72)
    print("SIF ML training discipline — training split only")
    print("=" * 72)

    if method and method != "all":
        methods = {
            "stratified_kfold": ml_training.stratified_kfold,
            "repeated_stratified": ml_training.repeated_stratified,
            "leave_one_out": ml_training.leave_one_out,
            "grouped": ml_training.grouped,
            "nested": ml_training.nested,
            "learning_curve": ml_training.learning_curve_method,
        }
        res = methods[method]() if method != "repeated_stratified" else methods[method]()
        print(json.dumps(res, indent=2, default=str))
        return

    report = ml_training.run_training_report()
    print("discipline:", json.dumps(report["discipline"], indent=2))
    for name, res in report["methods"].items():
        print("-" * 72)
        print(name)
        print(res.get("description", ""))
        if name == "learning_curve":
            for p in res["points"]:
                print(f"  {p['train_rows']:>6} rows ({p['fraction']:.0%})  "
                      f"train F1 {p['train_f1']:.3f}  CV F1 {p['cv_f1']:.3f}  "
                      f"gap {p['gap']:+.3f}")
            print("  diagnosis:", res["diagnosis"])
        else:
            for metric, a in res["aggregate"].items():
                print(f"  {metric:<9} {a['mean']:.3f} ± {a['std']:.3f}  "
                      f"[{a['ci95_low']:.3f}, {a['ci95_high']:.3f}]")
    tf = report.get("train_final")
    if tf:
        print("-" * 72)
        print("final model (fit on training split only):")
        print(f"  {tf['model']} on {tf['rows']} rows — train F1 {tf['train_f1']}")
        print(f"  {tf['note']}")
    print("-" * 72)
    test = ml_training.evaluate_test_once()
    if test.get("ok"):
        print("FINAL held-out TEST evaluation (one-shot, untouched):")
        print(f"  rows {test['test_rows']}  SIF+ {test['test_sif_positive']}  "
              f"P {test['precision']}  R {test['recall']}  "
              f"F1 {test['f1']}  acc {test['accuracy']}")
    else:
        print("final test evaluation:", test.get("note"))
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, default=str))
        return
    out = ml_training.write_report_markdown()
    print("=" * 72)
    print(f"markdown report written -> {out}")


if __name__ == "__main__":
    main()