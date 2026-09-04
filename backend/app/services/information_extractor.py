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


def _term_negated(lower: str, term: str) -> bool:
    """Generic barrier terms only count when a failure is signalled nearby.

    e.g. "LOTO was applied" must NOT add a barrier failure, but
    "LOTO tag was missing" must.
    """
    for nullify in lx.NULLIFY_PHRASES:
        if nullify in lower:
            lower = lower.replace(nullify, "")
    start = 0
    while True:
        pos = lower.find(term, start)
        if pos == -1:
            break
        window = lower[max(0, pos - 60) : pos + len(term) + 60]
        if any(tok in window for tok in lx.NEGATION_TOKENS):
            return True
        start = pos + len(term)
    return False


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
        if any(_term_negated(lower, t) for t in terms):
            barriers.append(barrier)
    return barriers


def extract_equipment(text: str) -> list[str]:
    lower = text.lower()
    equipment: list[str] = []
    for name, terms in lx.EQUIPMENT_TERMS.items():
        if any(t in lower for t in terms):
            equipment.append(name)
    return equipment


def extract_location(text: str) -> str | None:
    """Explicit location phrases when stated; otherwise None."""
    lower = text.lower()
    patterns = [
        ("loading bay", "Loading bay"),
        ("control room", "Control room"),
        ("pump room", "Pump room"),
        ("workshop", "Workshop"),
        ("yard", "Yard"),
        ("rooftop", "Rooftop"),
    ]
    for term, label in patterns:
        if term in lower:
            return label
    return None


def extract_all(
    text: str, matches: list[IndicatorMatch]
) -> dict:
    return {
        "activity": extract_activity(text),
        "hazards": extract_hazards(text, matches),
        "barrier_failure": extract_barrier_failures(text, matches),
        "equipment": extract_equipment(text),
        "location": extract_location(text),
        "unsafe_type": classify_act_condition(text),
    }