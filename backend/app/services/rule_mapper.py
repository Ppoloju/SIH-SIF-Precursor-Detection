"""Rule-condition mapping — "map out the conditions of the Life-Saving Rule".

For the primary Life-Saving Rule of a report this module checks each of the
rule's conditions (requirements / controls from ``safety_lexicon.RULE_CONDITIONS``)
against the report text and returns a per-condition verdict:

  * ``breached``       — the text shows the requirement was NOT met
                        (a matched failure phrase, or a control word sitting
                        next to a negation / failure word, e.g. "no harness",
                        "harness nahi", "guard removed").
  * ``in_place``       — the text shows the control was present / applied
                        (e.g. "LOTO was applied", "gas test passed") and no
                        failure signal sits near it.
  * ``not_verifiable`` — the report never mentions this requirement.

Matched SIF indicators are attributed first: each failure word in a matched
phrase is paired with the *nearest* control term it refers to, so "without a
harness and the scaffold lacked guardrails" correctly breaches the fall-
protection condition (nearest to "without") and the guardrail condition
(nearest to "lacked") — but NOT the scaffold-access condition, which is never
shown to have failed. Non-English failure phrases (Hinglish / Banglish /
Assamese) that embed an English control word are handled by the same pairing;
phrases the mapper cannot read (native-script text) produce one honest
"matched report phrase" row rather than a guessed condition.

This is a deterministic heuristic mapping for review — it never invents
evidence, and the statuses are meant to be validated by HSE.
"""

from __future__ import annotations

import re

from app.services import safety_lexicon as lx
from app.services.sif_detector import IndicatorMatch

# Clause connectors / sentence punctuation that bound the negation window so a
# failure in one clause never leaks into a neighbouring clause.
_CLAUSE_CONNECTORS = [
    " and ", " but ", " so ", " while ", " whereas ", " although ", " though ",
    " however ", " ; ", " , ",
]
_SENTENCE_END = ".!?;"

# All words that can flip a control mention to "failed": English negations,
# control-failure words, and non-English negations.
_NEGATION_WORDS: list[str] = sorted(
    set(lx.NEGATION_TOKENS) | set(lx.CONTROL_FAILURE_WORDS),
    key=len,
    reverse=True,
)
_FOREIGN_NEG_RE = re.compile(
    r"(?<![a-z0-9])" + "|".join(re.escape(t) for t in lx.FOREIGN_NEGATION_TOKENS) + r"(?![a-z0-9])"
)

_NULLIFY = tuple(lx.NULLIFY_PHRASES)


def _occurrences(lower: str, phrase: str) -> list[int]:
    """Every position of a phrase (prefix-aware for single tokens like
    'isolat' so 'isolated'/'isolating' match; guard-rail words excluded)."""
    positions: list[int] = []
    start = 0
    while True:
        pos = lower.find(phrase, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + max(len(phrase), 1)
    if " " not in phrase:
        # Single tokens must not be a suffix of an unrelated word (e.g.
        # "pit" in "spit", "edge" in "knowledge")…
        positions = [p for p in positions if p == 0 or not lower[p - 1].isalnum()]
        # …nor a prefix of a guard-rail word for the ambiguous "guard".
        blocks = lx.FOLLOW_BLOCKS.get(phrase)
        if blocks:
            filtered: list[int] = []
            for p in positions:
                tail = lower[p + len(phrase) : p + len(phrase) + 12]
                if not any(tail.startswith(b) for b in blocks):
                    filtered.append(p)
            positions = filtered
    return positions


def _strip_nullify(window: str) -> str:
    for phrase in _NULLIFY:
        window = window.replace(phrase, "")
    return window


def _bounded_window(lower: str, pos: int, length: int, before: int = 45, after: int = 30) -> str:
    """Region around a term, bounded by sentence punctuation AND clause
    connectors, so a "no/without" in an earlier clause can't flip a control
    that was actually present later in the sentence."""
    ws = max(0, pos - before)
    we = min(len(lower), pos + length + after)
    # Trim to the last sentence end before the term.
    for i in range(pos - 1, max(0, pos - before - 1), -1):
        if lower[i] in _SENTENCE_END:
            ws = i + 1
            break
    for i in range(pos + length, min(len(lower), pos + length + after)):
        if lower[i] in _SENTENCE_END:
            we = i
            break
    # Trim to the nearest clause connector on each side (search outward from
    # the term so a connector next to the term wins over a far-away one).
    for conn in _CLAUSE_CONNECTORS:
        idx = lower.rfind(conn, ws, pos)
        if idx != -1 and idx + len(conn) > ws:
            ws = idx + len(conn)
        idx = lower.find(conn, pos + length, we)
        if idx != -1 and idx < we:
            we = idx
    return _strip_nullify(lower[ws:we])


def _negated_window(lower: str, pos: int, length: int) -> bool:
    window = _bounded_window(lower, pos, length)
    if _FOREIGN_NEG_RE.search(window):
        return True
    return any(tok in window for tok in _NEGATION_WORDS)


def _failure_positions(lower: str) -> list[int]:
    """Positions of every negation/failure word in a phrase."""
    found: list[int] = []
    for tok in _NEGATION_WORDS:
        start = 0
        while True:
            pos = lower.find(tok, start)
            if pos == -1:
                break
            found.append(pos)
            start = pos + len(tok)
    return sorted(set(found))


def _quote(text: str, pos: int, length: int, max_len: int = 180) -> str:
    """The sentence (clipped) containing a match, for human-readable evidence."""
    start = pos
    end = pos + length
    while start > 0 and text[start - 1] not in _SENTENCE_END:
        start -= 1
    while end < len(text) and text[end] not in _SENTENCE_END:
        end += 1
    quote = text[start:end].strip()
    if len(quote) > max_len:
        quote = quote[: max_len - 1].rstrip() + "…"
    return quote


def _dedupe(items: list[str], limit: int = 3) -> list[str]:
    out: list[str] = []
    for it in items:
        if it and it not in out:
            out.append(it)
    return out[:limit]


def map_rule_conditions(
    text: str, rule: str | None, matches: list[IndicatorMatch]
) -> list[dict]:
    """Map a report's text to the conditions of its primary Life-Saving Rule.

    Returns a list of ``{condition, status, evidence}`` dicts (empty when no
    rule or no rule conditions are configured). Only ever additive: it never
    changes the SIF verdict, the rule or the priority.
    """
    if not rule or not text:
        return []
    conds = lx.RULE_CONDITIONS.get(rule)
    if not conds:
        return []

    lower = text.lower()
    n_conds = len(conds)
    statuses: list[str] = ["not_verifiable"] * n_conds
    evidence: list[list[str]] = [[] for _ in range(n_conds)]
    claimed_by_match: set[int] = set()

    # --- 1) Attribute matched indicator phrases to the control they name. ---
    # Each failure word inside a matched phrase is paired (greedily, by
    # distance) with the nearest control term of any condition.
    pending: list[IndicatorMatch] = [m for m in matches if m.rule == rule]

    for m in pending:
        ml = m.phrase.lower()
        fails = _failure_positions(ml)
        if not fails:
            continue  # positive-sounding indicator — nothing to attribute
        # (term_pos, fail_pos, cond_idx) candidates with distances, computed
        # on the matched phrase itself.
        candidates: list[tuple[int, int, int, int]] = []  # (dist, ci, tpos, fpos)
        for ci, cond in enumerate(conds):
            for term in cond.get("terms", []):
                for tpos in _occurrences(ml, term):
                    for fpos in fails:
                        dist = abs(tpos - fpos)
                        if dist <= 60:
                            candidates.append((dist, ci, tpos, fpos))
        if not candidates:
            continue
        claimed_conds: set[int] = set()
        used_fails: set[int] = set()
        for dist, ci, tpos, fpos in sorted(candidates):
            if ci in claimed_conds or fpos in used_fails:
                continue
            claimed_conds.add(ci)
            used_fails.add(fpos)
        if not claimed_conds:
            continue
        claimed_by_match.add(id(m))
        for ci in claimed_conds:
            statuses[ci] = "breached"
            evidence[ci].append(m.phrase)

    # --- 2) Literal breach anchors + control-term scans for the rest. -------
    for ci, cond in enumerate(conds):
        if statuses[ci] == "breached":
            continue
        breach = cond.get("breach", [])
        terms = cond.get("terms", [])

        # Literal breach phrases anywhere in the text.
        for bp in breach:
            if statuses[ci] == "breached":
                break
            for pos in _occurrences(lower, bp):
                evidence[ci].append(_quote(text, pos, len(bp)))
                statuses[ci] = "breached"
                break

        # Control-term presence scan (negation-aware, clause-bounded).
        # Conditions whose control is a *place* (scaffold / ladder) only ever
        # report "in place" from presence — breach must come from a matched
        # failure phrase or a literal anchor, never from proximity alone.
        presence_breach = cond.get("presence_breach", True)
        ok_markers = cond.get("ok_markers") or []
        if statuses[ci] == "not_verifiable":
            found = False
            for term in terms:
                for pos in _occurrences(lower, term):
                    found = True
                    if presence_breach and _negated_window(lower, pos, len(term)):
                        evidence[ci].append(_quote(text, pos, len(term)))
                        statuses[ci] = "breached"
                        break
                if statuses[ci] == "breached":
                    break
            if statuses[ci] == "not_verifiable" and found:
                # Location-like conditions need a positive marker before
                # "in place" is claimed; otherwise the mention alone stays
                # "not verifiable".
                marked = False
                if ok_markers:
                    for term in terms:
                        for pos in _occurrences(lower, term):
                            window = _bounded_window(lower, pos, len(term))
                            if any(mk in window for mk in ok_markers):
                                marked = True
                                break
                        if marked:
                            break
                else:
                    marked = True
                if marked:
                    statuses[ci] = "in_place"
                    for term in terms:
                        positions = _occurrences(lower, term)
                        if positions:
                            evidence[ci].append(_quote(text, positions[0], len(term)))
                            break

    rows = [
        {
            "condition": conds[ci]["condition"],
            "status": statuses[ci],
            "evidence": _dedupe(evidence[ci]),
        }
        for ci in range(n_conds)
    ]

    # Indicator phrases the mapper could not tie to a specific condition (e.g.
    # native-script text). Surface them honestly instead of guessing — unless
    # a condition row already quotes the same phrase.
    quoted: list[str] = [e for ev in evidence for e in ev]
    unmatched = [
        m
        for m in pending
        if id(m) not in claimed_by_match
        and not any(m.phrase in q for q in quoted)
    ]
    if unmatched:
        rows.append(
            {
                "condition": (
                    f"{rule} — a matched report phrase shows a required "
                    "control was not applied"
                ),
                "status": "breached",
                "evidence": _dedupe([m.phrase for m in unmatched]),
            }
        )

    return rows
