"""Evaluation harness over the labeled golden set.

Runs the deterministic engine (rules + multilingual layer — no LLM, so the
numbers are stable and reproducible) over ``app.data.golden_set`` and reports:

* SIF classification metrics (precision / recall / F1 / accuracy + confusion)
* per-Life-Saving-Rule precision / recall / F1 over the reference labels
* language / multilingual coverage (Hindi, Bengali, Assamese included)
* per-case detail for the UI table

Method note: a report is *positive for a rule* when the reference label lists
it; rule-level metrics aggregate over every case, so a report that legitimately
matches two rules counts in both (multi-label evaluation).
"""

from __future__ import annotations

import time

from app.data.golden_set import GOLDEN_CASES, GOLDEN_META
from app.services import multilingual, sif_detector
from app.services.analysis_pipeline import analyze_report
from app.services.safety_lexicon import RULE_ORDER


def _detected_rules(text: str) -> list[str]:
    """All rules detected for a report (English + foreign phrase layers)."""
    rules = {m.rule for m in sif_detector.detect_indicators(text)}
    rules |= {m.rule for m in multilingual.detect_foreign_indicators(text)}
    return sorted(rules, key=lambda r: RULE_ORDER.index(r) if r in RULE_ORDER else 99)


def _rule_metrics(expected_cases: list[bool], detected_cases: list[bool]) -> dict:
    tp = fp = fn = 0
    support = 0
    for i in range(len(GOLDEN_CASES)):
        expected = expected_cases[i] if i < len(expected_cases) else False
        detected = detected_cases[i] if i < len(detected_cases) else False
        if expected:
            support += 1
            if detected:
                tp += 1
            else:
                fn += 1
        elif detected:
            fp += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "support": support,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def run_evaluation() -> dict:
    started = time.time()
    n = len(GOLDEN_CASES)
    sif_tp = sif_fp = sif_fn = sif_tn = 0
    per_rule_expected: dict[str, list[bool]] = {r: [False] * n for r in RULE_ORDER}
    per_rule_detected: dict[str, list[bool]] = {r: [False] * n for r in RULE_ORDER}
    lang_stats: dict[str, dict] = {}
    multilingual_cases = 0
    multilingual_correct = 0
    details: list[dict] = []

    for i, case in enumerate(GOLDEN_CASES):
        text = case["text"]
        expected_sif = case["expect_sif"]
        expected_rules = case["expect_rules"]

        # Deterministic engine verdicts.
        result = analyze_report(text, use_llm=False)
        detected_sif = result["sif_potential"]
        detected_rules = _detected_rules(text)

        for rule in expected_rules:
            per_rule_expected[rule][i] = True
        for rule in detected_rules:
            per_rule_detected[rule][i] = True

        if expected_sif and detected_sif:
            sif_tp += 1
        elif not expected_sif and detected_sif:
            sif_fp += 1
        elif expected_sif and not detected_sif:
            sif_fn += 1
        else:
            sif_tn += 1

        # Language coverage.
        lang = case.get("lang", "en")
        stat = lang_stats.setdefault(
            lang, {"lang": lang, "cases": 0, "sif_correct": 0, "label": multilingual.label_for(lang)}
        )
        stat["cases"] += 1
        if expected_sif == detected_sif:
            stat["sif_correct"] += 1
        if lang != "en":
            multilingual_cases += 1
            if expected_sif == detected_sif:
                multilingual_correct += 1

        detail = {
            "id": case["id"],
            "lang": lang,
            "language_label": multilingual.label_for(lang),
            "text": text[:160],
            "expected_sif": expected_sif,
            "detected_sif": detected_sif,
            "sif_match": expected_sif == detected_sif,
            "expected_rules": expected_rules,
            "detected_rules": detected_rules,
            "rule_match": sorted(expected_rules) == sorted(detected_rules),
            "confidence": result.get("confidence"),
            "priority": result.get("priority"),
            "languages_detected": result.get("languages") or [],
        }
        details.append(detail)

    precision = sif_tp / (sif_tp + sif_fp) if (sif_tp + sif_fp) else 0.0
    recall = sif_tp / (sif_tp + sif_fn) if (sif_tp + sif_fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (sif_tp + sif_tn) / n

    rules_report = []
    for rule in RULE_ORDER:
        m = _rule_metrics(per_rule_expected[rule], per_rule_detected[rule])
        rules_report.append({"rule": rule, **m})

    languages_report = []
    for code in ("en", "hi", "hi-latn", "bn", "bn-latn", "as", "as-latn"):
        if code in lang_stats:
            s = lang_stats[code]
            s["sif_accuracy"] = round(100 * s["sif_correct"] / s["cases"], 1)
            languages_report.append(s)

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "dataset": GOLDEN_META,
        "sif_classification": {
            "tp": sif_tp, "fp": sif_fp, "fn": sif_fn, "tn": sif_tn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "accuracy": round(accuracy, 3),
        },
        "rules": rules_report,
        "languages": languages_report,
        "multilingual": {
            "cases": multilingual_cases,
            "sif_correct": multilingual_correct,
            "sif_accuracy": round(100 * multilingual_correct / multilingual_cases, 1)
            if multilingual_cases
            else None,
        },
        "cases": details,
        "runtime_ms": round((time.time() - started) * 1000),
        "methodology": (
            "Deterministic engine (rules + multilingual layer), no LLM. "
            "Rule metrics are multi-label: a case counts as a rule positive when "
            "the golden label lists that rule."
        ),
    }
