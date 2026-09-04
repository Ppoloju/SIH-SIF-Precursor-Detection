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


def _stratified_folds(k: int) -> list[list[int]]:
    """Deterministic stratified folds (no sklearn dependency).

    Every case index is bucketed by its stratum ``(expect_sif, lang)`` and
    the members of each stratum are dealt round-robin across the folds, so
    each fold mirrors the global SIF-positive ratio *and* the language mix
    as closely as a 35-case set allows.
    """
    strata: dict[tuple, list[int]] = {}
    for i, case in enumerate(GOLDEN_CASES):
        strata.setdefault((case["expect_sif"], case.get("lang", "en")), []).append(i)
    folds: list[list[int]] = [[] for _ in range(k)]
    for members in strata.values():
        for offset, idx in enumerate(members):
            folds[offset % k].append(idx)
    return folds


def _binary(tp: int, fp: int, fn: int, tn: int) -> dict:
    denom_p = tp + fp
    denom_r = tp + fn
    denom_a = tp + fp + fn + tn
    precision = tp / denom_p if denom_p else 0.0
    recall = tp / denom_r if denom_r else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round((tp + tn) / denom_a, 3) if denom_a else 0.0,
    }


def run_kfold_cv(k: int = 5) -> dict:
    """Stratified k-fold stability check over the golden set.

    The core engine is deterministic (no fitted parameters), so this is not
    training cross-validation — it answers the question the single-split
    numbers cannot: *are the headline metrics stable, or the luck of one
    case composition?* Each fold is a held-out slice stratified by
    (SIF label, language); the engine verdicts are computed once per case
    and then evaluated on every fold, so the fold-to-fold spread is purely
    compositional.

    Once HSE feedback accumulates, the same folds are the correct seam for
    true learning CV: train the adaptive signal-miner (app.services.adaptive)
    on k-1 folds and test on the held-out fold.
    """
    started = time.time()
    k = max(2, min(int(k), len(GOLDEN_CASES)))
    folds = _stratified_folds(k)

    # Engine verdict per case — computed once, reused by every fold.
    pred_sif: list[bool] = []
    for case in GOLDEN_CASES:
        pred_sif.append(analyze_report(case["text"], use_llm=False)["sif_potential"])

    fold_rows: list[dict] = []
    for fold_no, members in enumerate(folds, start=1):
        tp = fp = fn = tn = 0
        for i in members:
            expected = GOLDEN_CASES[i]["expect_sif"]
            detected = pred_sif[i]
            if expected and detected:
                tp += 1
            elif not expected and detected:
                fp += 1
            elif expected and not detected:
                fn += 1
            else:
                tn += 1
        langs: dict[str, int] = {}
        for i in members:
            langs[GOLDEN_CASES[i].get("lang", "en")] = langs.get(GOLDEN_CASES[i].get("lang", "en"), 0) + 1
        fold_rows.append({
            "fold": fold_no,
            "n": len(members),
            "sif_positive": sum(1 for i in members if GOLDEN_CASES[i]["expect_sif"]),
            **{k_: v for k_, v in _binary(tp, fp, fn, tn).items()},
            "languages": ", ".join(f"{c}×{n_}" for c, n_ in sorted(langs.items())),
        })

    def _agg(key: str) -> dict:
        vals = [f[key] for f in fold_rows]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = var ** 0.5
        return {
            "mean": round(mean, 3),
            "std": round(std, 3),
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            # Normal-approximation 95% CI over the folds.
            "ci95_low": round(mean - 1.96 * std / (len(vals) ** 0.5), 3),
            "ci95_high": round(mean + 1.96 * std / (len(vals) ** 0.5), 3),
        }

    return {
        "k": k,
        "n_cases": len(GOLDEN_CASES),
        "folds": fold_rows,
        "aggregate": {key: _agg(key) for key in ("precision", "recall", "f1", "accuracy")},
        "runtime_ms": round((time.time() - started) * 1000),
        "methodology": (
            "Stratified k-fold stability check: folds are dealt round-robin by "
            "(SIF label, language) stratum so every fold mirrors the global "
            "SIF-positive ratio and language mix. The engine is deterministic "
            "and is evaluated on each held-out fold — the spread measures "
            "stability across case composition, not model-training variance. "
            "Same folds become the train/test seam for adaptive-signal CV "
            "once HSE review feedback accumulates."
        ),
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
