"""Narrative layer — plain-language summaries + rule-based suggested actions.

Deterministic text generation from the structured analysis. Nothing here is
invented: every clause is drawn from the report text, matched indicators,
Life-Saving-Rule profile or the extracted structured fields. When the Groq
LLM is available it may rephrase these templates — never add facts.
"""

from __future__ import annotations

from app.services.safety_lexicon import RULES

_PROFILES: dict[str, dict] = {r["name"]: r for r in RULES}


def _lower_or(text: str | None, fallback: str) -> str:
    if not text:
        return fallback
    return text.lower()


def _evidence_quote(evidence: list[str], max_len: int = 110) -> str | None:
    if not evidence:
        return None
    quote = evidence[0]
    if len(quote) > max_len:
        quote = quote[: max_len - 1].rstrip() + "…"
    return quote


def build_summary(result: dict, text: str | None = None) -> str:
    """Three-part, groundable summary: what happened / why it matters / next."""
    evidence = result.get("evidence") or []
    quote = _evidence_quote(evidence)
    activity = result.get("activity")
    rule = result.get("life_saving_rule")
    hazards = result.get("hazards") or ([result["hazard"]] if result.get("hazard") else [])
    consequence = result.get("potential_consequence")
    barriers = result.get("barrier_failure") or []

    # --- 1. What happened (grounded in the report) -------------------------
    if quote:
        happened = (
            f"{activity.capitalize() if activity else 'Work'} was in progress when the "
            f'report recorded: \u201c{quote}\u201d.'
        )
    elif activity:
        happened = f"The report describes an issue during {activity.lower()} work."
    else:
        happened = "The report describes an unsafe act / condition observed on site."

    # --- 2. Why it matters --------------------------------------------------
    if result.get("sif_potential"):
        risk_parts = []
        if consequence:
            risk_parts.append(f"potential for {_lower_or(consequence, 'serious harm')}")
        if hazards:
            risk_parts.append(f"hazard: {hazards[0].lower()}")
        if rule:
            risk_parts.append(f"mapped to the Life-Saving Rule: {rule}")
        matters = (
            "This situation carries "
            + ("; ".join(risk_parts) if risk_parts else "serious-injury potential")
            + " — under slightly different circumstances it could have caused "
            "a serious injury or fatality."
        )
    else:
        matters = (
            "No serious-injury / fatality (SIF) precursor indicators were found — "
            "this reads as a routine observation rather than a high-potential event."
        )

    # --- 3. What should happen ----------------------------------------------
    action = result.get("recommended_follow_up")
    if not action and barriers:
        action = (
            "Reinstate and verify the affected control(s) before any similar work resumes"
            + (f" ({', '.join(barriers[:2])})." if barriers else ".")
        )
    if not action:
        action = "File the observation and include it in the next routine HSE review cycle."
    next_step = action

    return (
        f"What happened — {happened}\n\n"
        f"Why it matters — {matters}\n\n"
        f"Next step — {next_step}"
    )


def suggest_actions(result: dict) -> list[str]:
    """Concrete, rule-based corrective-action checklist (max ~5 items)."""
    rule = result.get("life_saving_rule")
    barriers = result.get("barrier_failure") or []
    priority = result.get("priority")
    actions: list[str] = []

    if not result.get("sif_potential"):
        return [
            "No SIF precursor detected — file under routine observations; no escalation required."
        ]

    profile = _PROFILES.get(rule) if rule else None
    if profile and profile.get("follow_up"):
        actions.append(profile["follow_up"])

    for barrier in barriers[:2]:
        actions.append(
            f"Verify and reinstate {barrier.lower()} before the next similar job starts; "
            "record who confirmed it and when."
        )

    if rule:
        actions.append(
            f"Brief the crew on the {rule.lower()} requirements for this activity "
            "(toolbox talk) and confirm the permit / checklists are in place."
        )

    if priority == "HIGH":
        actions.append("Escalate to HSE for same-day review and a physical site check.")
    elif priority == "MEDIUM":
        actions.append("Schedule an HSE review within 48 hours and add the site to the weekly inspection list.")

    # Keep the list short but complete.
    return actions[:5]


def tune_prompt_fragments() -> str:
    """Schema fragment used by the LLM prompt (kept in sync with LlmRefinement)."""
    return (
        "\\\"summary\\\": str|null (three short paragraphs: what happened / why it matters / next step), "
        "\\\"suggested_actions\\\": [str]"
    )
