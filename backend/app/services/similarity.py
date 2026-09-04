"""Similar-report search.

Deterministic, dependency-free similarity that works across English and
Indic-script text: token-overlap on the report text is combined with shared
*structured meaning* (Life-Saving Rule, hazard, barrier failure, activity).
Shared concepts dominate the score so two reports about the same precursor
rank highly even when their wording differs (e.g. a Hindi and an English
description of the same gas-test failure).

Scoring (max ~1.0):
  * token Jaccard of the two reports ........ 0.50
  * same Life-Saving Rule ................... 0.18
  * overlapping barrier failure ............. 0.12
  * same hazard ............................. 0.08
  * same activity (when both known) ......... 0.12
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Analysis, Report

_TOKEN_RE = re.compile(r"[a-z0-9']+|[\u0900-\u09ff]+")

_EN_STOP = {
    "the", "and", "was", "were", "with", "from", "that", "this", "have",
    "had", "has", "been", "not", "but", "for", "are", "his", "her", "was",
    "one", "two", "report", "reported", "said", "while", "during", "when",
    "then", "they", "their", "there", "him", "them", "who", "which", "will",
    "would", "should", "could", "also", "after", "before", "into", "onto",
    "than", "very", "just", "about", "every", "some", "any", "all", "more",
    "most", "other", "such", "only", "she", "his", "her", "its", "out",
    "had", "been", "being", "did", "does", "doing", "was", "were", "am",
}


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        t for t in _TOKEN_RE.findall(text.lower())
        if len(t) >= 3 and t not in _EN_STOP
    }


def pool_rows(db: Session, exclude_id: int, limit: int = 2500) -> list[dict]:
    rows = db.execute(
        select(Report, Analysis)
        .join(Analysis, Analysis.report_id == Report.id)
        .where(Report.id != exclude_id)
        .order_by(Report.id.desc())
        .limit(limit)
    ).all()
    out = []
    for report, analysis in rows:
        out.append(
            {
                "id": report.id,
                "report_id": report.report_id,
                "text": report.report_text or "",
                "rule": analysis.life_saving_rule,
                "hazard": analysis.hazard,
                "barriers": set(analysis.barrier_failure or []),
                "activity": analysis.activity,
            }
        )
    return out


def _score(a: dict, b_tokens: set[str], b: dict) -> tuple[float, dict]:
    """Similarity between pool row ``a`` and the query report ``b``."""
    a_tokens = _tokens(a["text"])
    if not a_tokens or not b_tokens:
        return 0.0, {}

    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    jaccard = inter / union if union else 0.0

    score = 0.50 * jaccard
    common: dict[str, str] = {}

    if a["rule"] and a["rule"] == b["rule"]:
        score += 0.18
        common["rule"] = a["rule"]
    barrier_overlap = a["barriers"] & (b["barriers"] or set())
    if barrier_overlap:
        score += 0.12
        common["barrier"] = sorted(barrier_overlap)
    if a["hazard"] and a["hazard"] == b["hazard"]:
        score += 0.08
        common["hazard"] = a["hazard"]
    if (
        a["activity"]
        and b["activity"]
        and a["activity"].lower() == b["activity"].lower()
    ):
        score += 0.12
        common["activity"] = a["activity"]

    return score, common


def find_similar(
    report: Report,
    db: Session | None = None,
    limit: int = 5,
    min_score: float = 0.16,
    pool: list[dict] | None = None,
) -> list[dict]:
    """Reports most similar to ``report`` (with the shared concepts they carry)."""
    analysis = report.analysis
    query = {
        "text": report.report_text or "",
        "rule": analysis.life_saving_rule if analysis else None,
        "hazard": analysis.hazard if analysis else None,
        "barriers": set(analysis.barrier_failure or []) if analysis else set(),
        "activity": analysis.activity if analysis else None,
    }
    q_tokens = _tokens(query["text"])
    if not q_tokens:
        return []

    if pool is None:
        if db is None:
            return []
        pool = pool_rows(db, exclude_id=report.id)

    scored: list[tuple[float, dict]] = []
    for a in pool:
        score, common = _score(a, q_tokens, query)
        if score >= min_score:
            scored.append(
                (
                    score,
                    {
                        "id": a["id"],
                        "report_id": a["report_id"],
                        "similarity": round(min(score, 0.99), 2),
                        "common_hazard": common.get("hazard"),
                        "common_activity": common.get("activity"),
                        "common_barrier": common.get("barrier"),
                        "common_rule": common.get("rule"),
                    },
                )
            )
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [entry for _, entry in scored[:limit]]
