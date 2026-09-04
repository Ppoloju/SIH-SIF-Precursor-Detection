"""Run the golden-set evaluation and print a terminal report.

Usage:
    python scripts/evaluate.py          # compact table
    python scripts/evaluate.py --json   # full JSON (for docs / CI)
"""

from __future__ import annotations

import json
import sys

if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.path.insert(0, "..")

from app.services.evaluation import run_evaluation  # noqa: E402


def _row(rule: dict) -> str:
    return (
        f"  {rule['rule']:<26} sup {rule['support']:>2} | "
        f"TP {rule['tp']:>2}  FP {rule['fp']:>2}  FN {rule['fn']:>2} | "
        f"P {rule['precision']:.2f}  R {rule['recall']:.2f}  F1 {rule['f1']:.2f}"
    )


def main() -> None:
    if "--json" in sys.argv:
        print(json.dumps(run_evaluation(), indent=2, ensure_ascii=False))
        return

    r = run_evaluation()
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
    print("=" * 72)


if __name__ == "__main__":
    main()
