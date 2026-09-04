"""Analysis pipeline orchestrator.

Report text in -> structured, explainable SIF analysis out.

Pipeline: preprocess -> indicator detection (English + Hindi/Assamese/Bengali)
-> rule mapping -> extraction -> narrative summary + suggested actions
-> risk scoring -> (optional) LLM refinement -> validated structured dict.

The LLM is strictly optional: if it fails or is unavailable the
deterministic result stands untouched.
"""

from __future__ import annotations

from app.services import (
    adaptive,
    information_extractor,
    multilingual,
    narrative,
    risk_scorer,
    rule_classifier,
    sif_detector,
)
from app.services.llm import refine_with_llm

MODEL_TAG = "rules-v1"  # deterministic baseline; "rules-v1+llm" when refined


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _sentence_at(text: str, pos: int) -> str:
    """The full sentence of the report containing a character position."""
    start = 0
    end = len(text)
    for i in range(pos, -1, -1):
        if text[i] in ".!?;\n":
            start = i + 1
            break
    for i in range(pos, len(text)):
        if text[i] in ".!?;\n":
            end = i + 1
            break
    return text[start:end].strip()


def build_explanation(
    text: str,
    evidence: list[str],
    hazard: str | None,
    rule: str | None,
    barriers: list[str],
) -> str:
    parts: list[str] = []
    if evidence:
        # Ground the explanation in the sentence containing the first evidence.
        idx = text.lower().find(evidence[0].lower())
        sentence = _sentence_at(text, idx) if idx != -1 else None
        if sentence and len(sentence) <= 400:
            parts.append(f'The report states: "{sentence}"')
        else:
            parts.append(f'The key phrase in the report is: "{evidence[0]}"')
    if hazard:
        parts.append(f"This is associated with {hazard.lower()}.")
    if rule:
        parts.append(f"It maps to the Life-Saving Rule: {rule}.")
    if barriers:
        parts.append(f"Key safety barrier(s) affected: {', '.join(barriers)}.")
    return " ".join(parts) if parts else "No SIF indicators detected in the report."


def analyze_report(text: str, use_llm: bool = True) -> dict:
    """Run the full pipeline. Returns a dict matching the Analysis schema."""
    text = _normalize_text(text)
    if not text:
        raise ValueError("Report text is required")

    # --- Detection: English rules first, then Hindi/Assamese/Bengali phrases.
    matches = sif_detector.detect_indicators(text)
    foreign = multilingual.detect_foreign_indicators(text)
    matches = matches + [m for m in foreign if not any(
        m.rule == k.rule and not (m.end <= k.start or m.start >= k.end) for k in matches
    )]

    risk = risk_scorer.assess(matches, text)
    primary_rule, rule_confidence = rule_classifier.classify_rule(matches)

    equipment = list(dict.fromkeys(
        information_extractor.extract_equipment(text)
        + multilingual.foreign_equipment(text)
    ))
    info = information_extractor.extract_all(text, matches)
    info["equipment"] = equipment

    evidence = list(dict.fromkeys(m.phrase for m in matches))
    hazards = info["hazards"]
    barriers = info["barrier_failure"]

    result: dict = {
        "sif_potential": risk["sif_potential"],
        "confidence": risk["confidence"],
        "priority": risk["priority"],
        "priority_factors": risk["priority_factors"],
        "hazard": hazards[0] if hazards else None,
        "hazards": hazards,
        "potential_consequence": (
            matches[0].consequence if matches else None
        ),
        "barrier_failure": barriers,
        "life_saving_rule": primary_rule,
        "rule_confidence": rule_confidence,
        "activity": info["activity"],
        "location": info["location"],
        "equipment": equipment,
        "unsafe_type": info["unsafe_type"],
        "evidence": evidence,
        "explanation": build_explanation(text, evidence, hazards[0] if hazards else None, primary_rule, barriers),
        "recommended_follow_up": None,
        "languages": multilingual.detect_languages(text),
        "summary": None,
        "suggested_actions": [],
        "model": MODEL_TAG,
        "llm_refined": False,
        "uncertainty_note": None,
    }

    # Narrative layer — deterministic plain-language summary + actions.
    result["summary"] = narrative.build_summary(result, text)
    result["suggested_actions"] = narrative.suggest_actions(result)

    # Optional LLM refinement — never allowed to contradict or invent evidence.
    if use_llm:
        refined = refine_with_llm(text, {k: v for k, v in result.items() if k != "priority_factors"})
        if refined is not None:
            if refined.explanation:
                result["explanation"] = refined.explanation
            if refined.recommended_follow_up:
                result["recommended_follow_up"] = refined.recommended_follow_up
            if refined.summary:
                result["summary"] = refined.summary
            if refined.suggested_actions:
                result["suggested_actions"] = refined.suggested_actions
            if refined.activity:
                result["activity"] = refined.activity
            if refined.location:
                result["location"] = refined.location
            if refined.hazard:
                result["hazard"] = refined.hazard
            if refined.barrier_failure:
                result["barrier_failure"] = refined.barrier_failure
            if refined.equipment:
                result["equipment"] = refined.equipment
            if refined.uncertainty_note:
                result["uncertainty_note"] = refined.uncertainty_note
            result["llm_refined"] = True
            result["model"] = f"{MODEL_TAG}+llm"

    # Learned reviewer signals (feedback -> retraining loop). Conservative.
    adaptive.apply_tuning(result, text)

    return result
