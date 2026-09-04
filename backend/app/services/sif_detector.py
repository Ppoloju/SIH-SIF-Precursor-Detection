"""Layer 1 — deterministic SIF-indicator detection.

Matches negation-aware indicator phrases from the safety lexicon against the
report text. Each match carries its own evidence (the exact phrase found),
hazard, consequence and failed barriers — making the detection explainable.

This layer never relies on the LLM; it is the reliable baseline.

Negation handling is scoped: phrases flagged `neg: True` only count when a
negation token (no / not / without / missing / bypassed / ...) appears near
them. Nullifying phrases such as "no incidents" or "no damage" are excluded
so positive reports do not produce false flags.
"""

import re
from dataclasses import dataclass, field

from app.services import safety_lexicon as lx

_WORD_CHARS = re.compile(r"[a-z0-9_\-']")


@dataclass
class IndicatorMatch:
    rule: str
    phrase: str  # evidence — exact text found in the original report
    start: int
    end: int
    hazard: str
    consequence: str
    barriers: list[str] = field(default_factory=list)
    negated: bool = False


def _word_bounds(text_lower: str, pos: int, length: int) -> tuple[int, int]:
    """Expand a match to whole-word boundaries for clean evidence."""
    start = pos
    end = pos + length
    while start > 0 and _WORD_CHARS.match(text_lower[start - 1]):
        start -= 1
    while end < len(text_lower) and _WORD_CHARS.match(text_lower[end]):
        end += 1
    return start, end


def _find_all(text_lower: str, phrase: str) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        pos = text_lower.find(phrase, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + len(phrase)
    return positions


def _negation_span(
    text_lower: str, pos: int, length: int
) -> tuple[int | None, int | None]:
    """Find negation-token spans within a 60-char window around a phrase.

    Returns (before_start, after_end) or Nones. Nullifying phrases (e.g.
    "no incidents") are stripped first so they never count as negation.
    """
    before_text = text_lower[max(0, pos - 60):pos]
    before_offset = max(0, pos - 60)
    after_text = text_lower[pos + length : pos + length + 60]
    after_offset = pos + length

    for nullify in lx.NULLIFY_PHRASES:
        before_text = before_text.replace(nullify, "")
        after_text = after_text.replace(nullify, "")

    # Closest negation token before the phrase (largest start position).
    before_start: int | None = None
    for tok in lx.NEGATION_TOKENS:
        idx = before_text.rfind(tok)
        if idx != -1:
            cand = before_offset + idx
            if before_start is None or cand > before_start:
                before_start = cand

    # Closest negation token after the phrase (smallest start position).
    after_end: int | None = None
    for tok in lx.NEGATION_TOKENS:
        idx = after_text.find(tok)
        if idx != -1:
            cand = after_offset + idx + len(tok)
            if after_end is None or cand < after_end:
                after_end = cand

    return before_start, after_end


def _window_negation(text_lower: str, pos: int, length: int) -> bool:
    before_start, after_end = _negation_span(text_lower, pos, length)
    return before_start is not None or after_end is not None


def _is_clean_match(text_lower: str, phrase: str, pos: int) -> bool:
    """Single-word phrases must start at a word boundary.

    Prevents e.g. "pressurized" from matching inside "depressurized" and
    "guard" from firing inside "guardrails". Multi-word phrases are
    space-delimited and safe as-is.
    """
    if " " in phrase:
        return True
    if pos > 0 and _WORD_CHARS.match(text_lower[pos - 1]):
        return False
    blocks = lx.FOLLOW_BLOCKS.get(phrase)
    if blocks:
        tail = text_lower[pos + len(phrase) : pos + len(phrase) + 12]
        if any(tail.startswith(b) for b in blocks):
            return False
    return True


def detect_indicators(text: str) -> list[IndicatorMatch]:
    """Return all matched safety indicators with evidence.

    Evidence is always the literal phrase found in the original report.
    Overlapping matches within a rule keep the longest phrase only.
    """
    if not text or not text.strip():
        return []

    text_lower = text.lower()
    matches: list[IndicatorMatch] = []

    for rule in lx.RULES:
        for ind in rule["indicators"]:
            phrase = ind["p"]
            for pos in _find_all(text_lower, phrase):
                if not _is_clean_match(text_lower, phrase, pos):
                    continue
                negated = _window_negation(text_lower, pos, len(phrase))
                if ind["neg"] and not negated:
                    continue
                start, end = _word_bounds(text_lower, pos, len(phrase))
                # Expand evidence to include the negation context so the
                # quote shown to the user carries the meaning.
                neg_before, neg_after = _negation_span(text_lower, pos, len(phrase))
                if neg_before is not None:
                    start = min(start, neg_before)
                if neg_after is not None:
                    end = max(end, neg_after)
                evidence = text[start:end].strip(" ,;.:\"'")
                matches.append(
                    IndicatorMatch(
                        rule=rule["name"],
                        phrase=evidence,
                        start=start,
                        end=end,
                        hazard=rule["hazard"],
                        consequence=rule["consequence"],
                        barriers=list(rule["barriers"]),
                        negated=negated,
                    )
                )

    # Keep the longest non-overlapping match per rule (e.g. "without isolating"
    # instead of just "isolat" at the same spot).
    kept: list[IndicatorMatch] = []
    for m in sorted(matches, key=lambda m: (m.end - m.start), reverse=True):
        if any(
            k.rule == m.rule and not (m.end <= k.start or m.start >= k.end)
            for k in kept
        ):
            continue
        kept.append(m)

    # Order matches by position in the report.
    kept.sort(key=lambda m: (m.start, -len(m.phrase)))
    return kept


def has_exposure(text: str) -> bool:
    """Heuristic: does the report suggest people are exposed to the hazard?"""
    lower = text.lower()
    return any(t in lower for t in lx.EXPOSURE_TERMS)


def classify_act_condition(text: str) -> str | None:
    """Distinguish Unsafe Act / Unsafe Condition when the text supports it."""
    lower = text.lower()
    is_act = any(a in lower for a in lx.ACT_ACTORS)
    is_condition = any(c in lower for c in lx.CONDITION_WORDS)
    if is_act and not is_condition:
        return lx.UNSAFE_ACT
    if is_condition and not is_act:
        return lx.UNSAFE_CONDITION
    if is_act and is_condition:
        return lx.UNSAFE_ACT  # people acting around a faulty condition -> act-led
    return None