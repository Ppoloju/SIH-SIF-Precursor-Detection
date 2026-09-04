"""Life-Saving Rule mapping.

The primary rule is the rule with the most matched indicators (ties broken
by the configured rule order). Confidence grows with the number of matched
indicators. This is hybrid-friendly: rules first, semantic/LLM refinement
can be layered on top later.
"""

from app.services import safety_lexicon as lx
from app.services.sif_detector import IndicatorMatch


def classify_rule(matches: list[IndicatorMatch]) -> tuple[str | None, float]:
    """Return (primary rule, confidence) from matched indicators."""
    if not matches:
        return None, 0.0

    counts: dict[str, int] = {}
    for m in matches:
        counts[m.rule] = counts.get(m.rule, 0) + 1

    best_rule = max(
        counts,
        key=lambda r: (
            counts[r],
            -lx.RULE_ORDER.index(r) if r in lx.RULE_ORDER else 0,
        ),
    )
    total = sum(counts.values())
    confidence = min(0.98, 0.60 + 0.12 * counts[best_rule])
    return best_rule, round(confidence, 2)


def rules_with_counts(matches: list[IndicatorMatch]) -> list[dict]:
    """All rules matched, with counts, for analytics."""
    counts: dict[str, int] = {}
    for m in matches:
        counts[m.rule] = counts.get(m.rule, 0) + 1
    ordered = sorted(
        counts.items(),
        key=lambda kv: (kv[1], -lx.RULE_ORDER.index(kv[0]) if kv[0] in lx.RULE_ORDER else 0),
        reverse=True,
    )
    return [{"rule": rule, "count": count} for rule, count in ordered]