"""Structured information extraction (deterministic layer).

Extracts activity, hazards, barrier failures, equipment and unsafe-act/
condition from the report text using the safety lexicon. Values that cannot
be determined are returned as None so callers can render "Not specified"
instead of inventing content.
"""

from app.services import safety_lexicon as lx
from app.services.sif_detector import IndicatorMatch, classify_act_condition


def extract_activity(text: str) -> str | None:
    """Best-guess activity.

    Explicitly-stated activity words win first; otherwise the most specific
    lexicon entry with any hit is used.
    """
    lower = text.lower()
    explicit = [
        ("Maintenance", ["maintenance", "servicing", "repair"]),
        ("Hot work", ["welding", "welded", "grinding", "hot work"]),
        ("Excavation", ["excavation", "excavating", "trench", "digging"]),
        ("Driving", ["driving", "reversing", "speeding"]),
        ("Electrical work", ["electrician", "electrical"]),
        ("Confined-space entry", ["confined space", "entered the tank", "entered the vessel"]),
        ("Working at height", ["working at height", "work at height"]),
    ]
    for activity, terms in explicit:
        if any(t in lower for t in terms):
            return activity
    for activity, terms in lx.ACTIVITY_TERMS.items():
        if any(t in lower for t in terms):
            return activity
    return None


def extract_hazards(text: str, matches: list[IndicatorMatch]) -> list[str]:
    """Hazards from matched rules, plus extra hazard vocabulary hits."""
    hazards: list[str] = []
    for m in matches:
        if m.hazard not in hazards:
            hazards.append(m.hazard)
    lower = text.lower()
    for hazard, terms in lx.EXTRA_HAZARDS.items():
        if hazard in hazards:
            continue
        if any(t in lower for t in terms):
            hazards.append(hazard)
    return hazards


def _term_failed(lower: str, term: str) -> bool:
    """A generic barrier term counts as failed only when a failure word sits
    in its clause-bounded neighbourhood (e.g. "LOTO was applied" must NOT add
    a barrier failure, but "LOTO tag was missing" / "guard removed" must).

    Word-block handling (from rule_mapper) stops "guard" inside "guardrails"
    from flagging Machine Guarding, and clause boundaries stop "without a
    harness … and the scaffold lacked guardrails" from flagging the wrong
    barrier group.
    """
    from app.services.rule_mapper import _negated_window, _occurrences

    return any(
        _negated_window(lower, pos, len(term))
        for pos in _occurrences(lower, term)
    )


def extract_barrier_failures(text: str, matches: list[IndicatorMatch]) -> list[str]:
    """Failed barriers: the primary barrier of each matched rule, plus any
    generic barrier vocabulary whose failure is signalled in the text.

    Only the rule's primary (most relevant) barrier is used so barrier
    analytics reflect genuinely-affected controls rather than the full rule
    profile.
    """
    barriers: list[str] = []
    seen_rules: set[str] = set()
    for m in matches:
        if m.rule in seen_rules or not m.barriers:
            continue
        seen_rules.add(m.rule)
        primary = m.barriers[0]
        if primary not in barriers:
            barriers.append(primary)
    lower = text.lower()
    for barrier, terms in lx.BARRIER_TERMS.items():
        if barrier in barriers:
            continue
        if any(_term_failed(lower, t) for t in terms):
            barriers.append(barrier)
    return barriers


def extract_equipment(text: str) -> list[str]:
    lower = text.lower()
    equipment: list[str] = []
    for name, terms in lx.EQUIPMENT_TERMS.items():
        if any(t in lower for t in terms):
            equipment.append(name)
    return equipment


def extract_location(text: str) -> tuple[str | None, str | None]:
    """Best-effort work-area location, and the term that suggested it.

    Returns (label, evidence_term). The label is ``None`` when the report
    never describes a place. The evidence term lets the caller explain that
    the location was *inferred from the text* rather than stated outright
    (e.g. "roof" -> "Roof / elevated work area").
    """
    lower = text.lower()
    for term, label in lx.LOCATION_TERMS:
        if term in lower:
            return label, term
    return None, None


def extract_all(
    text: str, matches: list[IndicatorMatch]
) -> dict:
    location, location_term = extract_location(text)
    return {
        "activity": extract_activity(text),
        "hazards": extract_hazards(text, matches),
        "barrier_failure": extract_barrier_failures(text, matches),
        "equipment": extract_equipment(text),
        "location": location,
        "location_evidence": location_term,
        "unsafe_type": classify_act_condition(text),
    }