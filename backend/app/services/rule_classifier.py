"""Life-Saving Rule mapping.

The primary rule is the rule with the most matched indicators (ties broken
by the configured rule order). When no indicator is detected, a weighted
lexical profile matcher maps the report to the closest canonical rule with a
low confidence score rather than leaving the report unclassified.
"""

import re

from app.services import safety_lexicon as lx
from app.services.sif_detector import IndicatorMatch


def _profile_score(text: str, rule: dict) -> float:
    """Score text overlap with a rule profile for the no-indicator fallback."""
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    if not tokens:
        return 0.0

    profile = " ".join(
        [
            rule["name"],
            rule.get("hazard", ""),
            rule.get("consequence", ""),
            rule.get("description", ""),
            rule.get("follow_up", ""),
            " ".join(rule.get("barriers", [])),
            " ".join(i["p"] for i in rule.get("indicators", [])),
        ]
    )
    profile_tokens = re.findall(r"[a-z0-9]+", profile.lower())
    profile_counts = {token: profile_tokens.count(token) for token in set(profile_tokens)}
    return sum(min(profile_counts[token], 3) for token in tokens if token in profile_counts)


def _fallback_rule(text: str) -> tuple[str, float]:
    scored = [(_profile_score(text, rule), rule["name"]) for rule in lx.RULES]
    best_score, best_rule = max(
        scored,
        key=lambda item: (item[0], -lx.RULE_ORDER.index(item[1])),
    )
    if best_score <= 0:
        # Keep every report classified while making the uncertainty explicit.
        return lx.RULE_ORDER[0], 0.10
    return best_rule, round(min(0.55, 0.15 + best_score * 0.05), 2)


def classify_rule(
    matches: list[IndicatorMatch], text: str | None = None
) -> tuple[str | None, float]:
    """Return (primary rule, confidence), with a text-based fallback."""
    if not matches:
        return _fallback_rule(text or "")

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