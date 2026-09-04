"""Analysis pipeline orchestrator.

Report text in -> structured, explainable SIF analysis out.

Pipeline: preprocess -> indicator detection (English + Hindi/Assamese/Bengali)
-> rule mapping -> extraction -> rule-condition mapping (which conditions of
the Life-Saving Rule the text shows as breached / in place / unverifiable)
-> narrative summary + suggested actions -> risk scoring -> (optional) LLM
refinement -> validated structured dict.

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
    rule_mapper,
    sif_detector,
)
from app.services.llm import refine_with_llm

MODEL_TAG = "rules-v1"  # deterministic baseline; "rules-v1+llm" when refined


def _normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and handling edge cases."""
    if not text or not isinstance(text, str):
        return ""
    # Remove excessive whitespace while preserving sentence structure
    text = " ".join(text.split())
    # Remove common encoding issues
    text = text.replace("\xa0", " ").replace("\u200b", "")
    # Limit maximum length to prevent processing issues
    if len(text) > 50000:
        text = text[:50000] + "..."
    return text.strip()


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
    rule_conditions: list[dict] | None = None,
    inferred: dict[str, str] | None = None,
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
    # Which conditions of the mapped Life-Saving Rule the text shows as broken.
    breached = [c["condition"] for c in (rule_conditions or []) if c["status"] == "breached"]
    if breached:
        parts.append(
            "Rule conditions indicated as breached: " + "; ".join(breached[:4]) + "."
        )
    # Honest note when a structured field was not stated but inferred.
    for field, reason in (inferred or {}).items():
        parts.append(
            f"{field.capitalize()} is not stated explicitly in the report — "
            f"{reason}."
        )
    return " ".join(parts) if parts else "No SIF indicators detected in the report."


def analyze_report(text: str, use_llm: bool = True) -> dict:
    """Run the full pipeline. Returns a dict matching the Analysis schema."""
    try:
        text = _normalize_text(text)
        if not text:
            raise ValueError("Report text is required")
    except Exception as e:
        raise ValueError(f"Text preprocessing failed: {str(e)}")

    # --- Detection: English rules first, then Hindi/Assamese/Bengali phrases.
    try:
        matches = sif_detector.detect_indicators(text)
        foreign = multilingual.detect_foreign_indicators(text)
        matches = matches + [m for m in foreign if not any(
            m.rule == k.rule and not (m.end <= k.start or m.start >= k.end) for k in matches
        )]
    except Exception as e:
        raise ValueError(f"Indicator detection failed: {str(e)}")

    try:
        risk = risk_scorer.assess(matches, text)
        primary_rule, rule_confidence = rule_classifier.classify_rule(matches, text)
    except Exception as e:
        raise ValueError(f"Risk assessment failed: {str(e)}")

    try:
        equipment = list(dict.fromkeys(
            information_extractor.extract_equipment(text)
            + multilingual.foreign_equipment(text)
        ))
        info = information_extractor.extract_all(text, matches)
        info["equipment"] = equipment
    except Exception as e:
        raise ValueError(f"Information extraction failed: {str(e)}")

    evidence = list(dict.fromkeys(m.phrase for m in matches))
    hazards = info["hazards"]
    barriers = info["barrier_failure"]

    # Structured fields the report never states outright are still answered
    # from the text when the context makes them clear — always flagged as
    # inferred in the explanation rather than silently invented.
    inferred: dict[str, str] = {}
    fallback_rule = not matches and primary_rule is not None
    if fallback_rule:
        inferred["life_saving_rule"] = (
            f"selected by low-confidence lexical matching ({rule_confidence:.2f})"
        )
    activity = info["activity"]
    if not activity and primary_rule:
        from app.services.safety_lexicon import RULE_TO_ACTIVITY

        fallback = RULE_TO_ACTIVITY.get(primary_rule)
        if fallback:
            activity = fallback
            inferred["activity"] = f"inferred from the mapped rule ({primary_rule})"
    location = info["location"]
    if location and info.get("location_evidence"):
        inferred["location"] = (
            f"inferred from the text (mentions '{info['location_evidence']}')"
        )

    # Map the report text onto the conditions of the detected Life-Saving Rule.
    rule_conditions = rule_mapper.map_rule_conditions(text, primary_rule, matches)

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
        "activity": activity,
        "location": location,
        "equipment": equipment,
        "unsafe_type": info["unsafe_type"],
        "evidence": evidence,
        "rule_conditions": rule_conditions,
        "explanation": build_explanation(
            text, evidence, hazards[0] if hazards else None, primary_rule, barriers,
            rule_conditions=rule_conditions, inferred=inferred,
        ),
        "recommended_follow_up": None,
        "languages": multilingual.detect_languages(text),
        "summary": None,
        "suggested_actions": [],
        "model": MODEL_TAG,
        "llm_refined": False,
        "uncertainty_note": None,
    }
    if fallback_rule:
        result["uncertainty_note"] = (
            "No direct Life-Saving Rule indicator was detected. The displayed rule "
            "was selected by the low-confidence text-profile fallback and requires HSE review."
        )

    # Narrative layer — deterministic plain-language summary + actions.
    result["summary"] = narrative.build_summary(result, text)
    breached = [c["condition"] for c in rule_conditions if c["status"] == "breached"]
    if breached:
        result["summary"] += (
            "\n\nLife-Saving-Rule conditions breached — "
            + "; ".join(breached[:4])
        )
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
