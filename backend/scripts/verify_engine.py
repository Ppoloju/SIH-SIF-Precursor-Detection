"""Quick engine verification (dev utility).

Runs the pipeline over the synthetic demo dataset + edge cases and reports
agreement with the expected labels. This is a dev check, not the formal
evaluation harness.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.demo_reports import demo_report_rows  # noqa: E402
from app.services.analysis_pipeline import analyze_report  # noqa: E402

EDGE_CASES = [
    ("", "empty -> ValueError"),
    ("Housekeeping issue: tools left on the walkway.", "non-SIF"),
    ("LOTO was applied and verified before work started.", "non-SIF positive"),
    ("Hot work was performed with a permit and fire watch present.", "non-SIF positive"),
    ("Worker entered the confined space after gas testing passed and a standby man was present.", "non-SIF positive"),
    ("The line was pressurized at 100 bar when the flange was opened.", "SIF energy"),
]


def main() -> None:
    rows = demo_report_rows()
    sif_mismatch = 0
    rule_mismatch = 0
    priorities: Counter = Counter()
    print(f"{'id':<10} {'exp':<4} {'got':<5} {'conf':<5} {'prio':<7} {'rule':<24} {'activity':<22} {'barriers'}")
    for r in rows:
        res = analyze_report(r["text"], use_llm=False)
        got = "SIF" if res["sif_potential"] else "non"
        exp = "SIF" if r["expected_sif"] else "non"
        priorities[res["priority"]] += 1
        if got != exp:
            sif_mismatch += 1
            print(f"  !! SIF mismatch {r['report_id']}: expected {exp}, got {got}")
        # Expected rules are only meaningful for reports expected to be SIF.
        if r["expected_sif"] and r["expected_rule"] and res["life_saving_rule"] != r["expected_rule"]:
            rule_mismatch += 1
            print(f"  !! RULE mismatch {r['report_id']}: expected {r['expected_rule']}, got {res['life_saving_rule']}")

    print()
    print(f"SIF agreement: {33 - sif_mismatch}/33 expected-SIF detected correctly")
    print(f"Rule agreement: {45 - rule_mismatch}/45")
    print(f"Priority spread: {dict(priorities)}")

    print("\n--- Edge cases ---")
    for text, label in EDGE_CASES:
        try:
            res = analyze_report(text, use_llm=False)
            print(f"[{label}] sif={res['sif_potential']} prio={res['priority']} rule={res['life_saving_rule']}")
        except ValueError as exc:
            print(f"[{label}] -> ValueError: {exc}")

    print("\n--- Example explanation (spec report) ---")
    res = analyze_report(
        "During maintenance, the technician started work on a pipeline without properly isolating the energy source.",
        use_llm=False,
    )
    print("evidence:", res["evidence"])
    print("barriers:", res["barrier_failure"])
    print("explanation:", res["explanation"])


if __name__ == "__main__":
    main()