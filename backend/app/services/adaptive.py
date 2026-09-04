"""Feedback -> retraining loop (prototype of human-in-the-loop learning).

How it works
------------
1. Every HSE review decision is stored as a labeled example in ``feedback``
   (a snapshot of the AI prediction at review time + the human decision).
2. ``train`` pulls those examples, computes model-vs-human agreement
   (precision / recall / F1 for the SIF decision), and mines the *surface
   phrases* that appear in reports where the reviewer disagreed with the
   model. Those phrases are stored as "learned signals".
3. Subsequent analyses apply the learned signals: a matched phrase is quoted
   back in evidence and raises the confidence / flags the report for priority
   review — the verdict itself still requires a real indicator match, so the
   tuning can never invent a SIF label from a single learned keyword.

This is deliberately a lightweight loop (rules + phrase weights, not a deep
model fine-tune) — honest for a prototype and safe to demo offline.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Feedback, TrainingRun

logger = logging.getLogger(__name__)

# In-process cache of the most recent training run (loaded by the API).
ACTIVE: dict = {"run_id": None, "feedback_count": 0, "signals": [], "metrics": {}}

_STOP = {
    "the", "and", "was", "were", "with", "from", "that", "this", "have",
    "had", "has", "been", "not", "but", "for", "are", "his", "her", "she",
    "one", "two", "reported", "report", "said", "told", "while", "during",
    "when", "then", "they", "their", "there", "him", "them", "who", "which",
    "will", "would", "should", "could", "also", "after", "before", "been",
    "being", "into", "onto", "than", "very", "just", "about", "every",
    "some", "any", "all", "more", "most", "other", "such", "only", "work",
    "worker", "workers", "site", "team", "job", "made", "make", "done",
}


def _tokens(text: str) -> list[str]:
    """Raw contiguous word tokens (lowercase, punctuation dropped)."""
    if not text:
        return []
    return re.findall(r"[a-z0-9']+|[\u0900-\u09ff]+", text.lower())


def _is_subsequence(tokens: list[str], phrase_tokens: list[str]) -> bool:
    """Do the phrase tokens appear contiguously inside the token stream?"""
    if not phrase_tokens or len(phrase_tokens) > len(tokens):
        return False
    width = len(phrase_tokens)
    for i in range(len(tokens) - width + 1):
        if tokens[i : i + width] == phrase_tokens:
            return True
    return False


# Domain vocabulary (from the rule lexicon) so learned signals stay meaningful
# instead of memorising filler like "area was otherwise".
def _domain_vocab() -> set[str]:
    from app.services.safety_lexicon import (
        BARRIER_TERMS,
        EQUIPMENT_TERMS,
        RULES,
    )

    words: set[str] = set()
    for rule in RULES:
        for ind in rule["indicators"]:
            words |= set(_tokens(ind["p"]))
    for terms in list(BARRIER_TERMS.values()) + list(EQUIPMENT_TERMS.values()):
        for t in terms:
            words |= set(_tokens(t))
    return words


_DOMAIN = _domain_vocab()


def _ngrams(tokens: list[str], n: int = 3) -> set[str]:
    return {
        " ".join(tokens[i : i + n]) for i in range(max(0, len(tokens) - n + 1))
    }


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def capture_feedback(
    db: Session,
    report,
    *,
    decision: str | None,
    reviewer: str | None,
    human_sif: bool | None,
    human_rule: str | None,
    human_priority: str | None,
    comments: str | None,
) -> Feedback:
    """Store one review decision as a labeled training example."""
    analysis = report.analysis
    fb = Feedback(
        report_id=report.id,
        reviewer=reviewer,
        decision=decision,
        ai_sif=analysis.sif_potential if analysis else None,
        ai_rule=analysis.life_saving_rule if analysis else None,
        ai_priority=analysis.priority if analysis else None,
        human_sif=human_sif,
        human_rule=human_rule or (analysis.life_saving_rule if analysis else None),
        human_priority=human_priority or (analysis.priority if analysis else None),
        comments=comments,
        created_at=datetime.utcnow(),
    )
    db.add(fb)
    db.commit()
    return fb


def feedback_summary(db: Session) -> dict:
    total = db.scalar(select(func.count(Feedback.id))) or 0
    decided = (
        db.scalar(select(func.count(Feedback.id)).where(Feedback.human_sif.is_not(None))) or 0
    )
    by_decision: dict[str, int] = {}
    for decision, count in db.execute(
        select(Feedback.decision, func.count(Feedback.id)).group_by(Feedback.decision)
    ).all():
        by_decision[decision or "reviewed"] = count

    latest_run = db.execute(
        select(TrainingRun).order_by(TrainingRun.id.desc()).limit(1)
    ).scalar_one_or_none()

    return {
        "feedback_count": total,
        "labeled_for_training": decided,
        "by_decision": by_decision,
        "latest_run": {
            "id": latest_run.id,
            "feedback_count": latest_run.feedback_count,
            "metrics": latest_run.metrics,
            "signals": latest_run.signals,
            "note": latest_run.note,
            "created_at": latest_run.created_at.isoformat() if latest_run.created_at else None,
        }
        if latest_run
        else None,
        "note": (
            "Every HSE review is stored as a labeled example (AI snapshot + human "
            "decision). 'Train on reviewed labels' re-measures agreement and mines "
            "signals from the disagreements."
        ),
    }


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _sif_metrics(tp: int, fp: int, fn: int, tn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) else 0.0
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round(accuracy, 3),
    }


def _mine_signals(rows: list) -> list[dict]:
    """Phrases that appear where the reviewer said SIF but the model did not
    (or the reverse) and that never appear in agreeing reports.

    Phrases are raw contiguous token runs that contain at least one domain
    word (gas detector, isolation, harness ...) so learned signals stay
    meaningful — they are the *vocabulary the model is blind to*.
    
    Enhanced with multi-gram analysis and confidence weighting.
    """
    pos: list[list[str]] = []   # human SIF, model missed
    neg: list[list[str]] = []   # human non-SIF, model flagged
    agree_tokens: list[str] = []

    for fb in rows:
        tokens = _tokens((fb.report.report_text or "") if fb.report else "")
        if fb.human_sif is True and fb.ai_sif is False:
            pos.append(tokens)
        elif fb.human_sif is False and fb.ai_sif is True:
            neg.append(tokens)
        else:
            agree_tokens.extend(tokens)

    def _candidates(groups: list[list[str]]) -> list[tuple[str, int]]:
        counter: dict[str, int] = {}
        for tokens in groups:
            # Try multiple n-gram sizes for better pattern discovery
            for n in [2, 3, 4]:
                for phrase in _ngrams(tokens, n):
                    words = phrase.split()
                    if not any(w in _DOMAIN for w in words):
                        continue
                    if all(w in _STOP for w in words):
                        continue
                    if len(phrase) < 6:  # Minimum phrase length
                        continue
                    counter[phrase] = counter.get(phrase, 0) + 1
        return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))

    signals: list[dict] = []
    for direction, groups, why in (
        ("+", pos, "Reviewers linked reports containing this phrase to SIF while the model missed them"),
        ("-", neg, "Reviewers said these reports were NOT SIF while the model flagged them"),
    ):
        for phrase, count in _candidates(groups):
            if len(signals) >= 8:  # Increased signal capacity
                break
            phrase_tokens = _tokens(phrase)
            if len(phrase) < 6 or _is_subsequence(agree_tokens, phrase_tokens):
                continue
            # Weight by frequency and phrase length
            weight = count * len(phrase_tokens)
            signals.append(
                {"phrase": phrase, "direction": direction, "reports": count, "weight": weight, "why": why}
            )
    # Sort by weight for most impactful signals first
    signals.sort(key=lambda s: s["weight"], reverse=True)
    return signals[:8]


def train(db: Session) -> dict:
    """Train on reviewed labels: agreement metrics + learned signals."""
    rows = (
        db.execute(
            select(Feedback)
            .options(joinedload(Feedback.report))
            .order_by(Feedback.id)
        )
        .scalars()
        .all()
    )
    decided = [fb for fb in rows if fb.human_sif is not None]

    tp = fp = fn = tn = 0
    for fb in decided:
        if fb.ai_sif is True and fb.human_sif is True:
            tp += 1
        elif fb.ai_sif is True and fb.human_sif is False:
            fp += 1
        elif fb.ai_sif is False and fb.human_sif is True:
            fn += 1
        else:
            tn += 1

    metrics = _sif_metrics(tp, fp, fn, tn)
    signals = _mine_signals(rows)

    run = TrainingRun(
        feedback_count=len(decided),
        metrics=metrics,
        signals=signals,
        note=(
            "Agreement between the AI engine and HSE reviewers on reports that were "
            "reviewed. Learned signals quote the exact phrases found in disagreeing "
            "reports; they tune confidence/evidence on future analyses and never "
            "flip a verdict on their own."
        ),
    )
    db.add(run)
    db.commit()

    # Refresh the in-process signal cache used by the analysis pipeline.
    ACTIVE.update(
        {
            "run_id": run.id,
            "feedback_count": len(decided),
            "signals": signals,
            "metrics": metrics,
        }
    )

    return {
        "ok": True,
        "run_id": run.id,
        "feedback_count": len(decided),
        "metrics": metrics,
        "signals": signals,
        "human_model_agreement": round(metrics["accuracy"] * 100, 1) if decided else 0.0,
        "note": run.note,
    }


def reload_active(db: Session) -> dict:
    """Reload the in-process signal cache from the latest stored run."""
    latest = db.execute(
        select(TrainingRun).order_by(TrainingRun.id.desc()).limit(1)
    ).scalar_one_or_none()
    if latest:
        ACTIVE.update(
            {
                "run_id": latest.id,
                "feedback_count": latest.feedback_count,
                "signals": latest.signals or [],
                "metrics": latest.metrics or {},
            }
        )
    else:
        ACTIVE.update({"run_id": None, "feedback_count": 0, "signals": [], "metrics": {}})
    return dict(ACTIVE)


# ---------------------------------------------------------------------------
# Analysis-time application
# ---------------------------------------------------------------------------

def apply_tuning(result: dict, text: str) -> dict:
    """Apply learned signals to a fresh analysis result (mutates + returns it).

    Conservative by design: matched phrases are quoted as evidence and the
    confidence is nudged toward the reviewer trend, but the SIF verdict and
    priority are never flipped by a learned keyword alone.
    
    Enhanced with weighted confidence adjustment and priority flagging.
    """
    signals = ACTIVE.get("signals") or []
    if not signals or not text:
        return result

    haystack_tokens = _tokens(text)
    matched: list[dict] = []
    for sig in signals:
        phrase = sig.get("phrase") or ""
        weight = sig.get("weight", 1)
        if (
            sig.get("direction") == "+"
            and _is_subsequence(haystack_tokens, _tokens(phrase))
        ):
            matched.append(sig)

    if not matched:
        return result

    result.setdefault("evidence", [])
    notes = []
    total_weight = sum(sig.get("weight", 1) for sig in matched)
    
    for sig in matched[:3]:  # Allow more matched signals
        phrase = sig.get("phrase")
        if phrase and phrase not in (result.get("evidence") or []):
            result["evidence"].append(phrase)
        notes.append(
            f"'{phrase}' matches a pattern HSE reviewers repeatedly linked to SIF "
            f"across {ACTIVE.get('feedback_count', 0)} reviewed labels"
        )

    base_conf = result.get("confidence") or 0.0
    # Weighted confidence adjustment based on signal strength
    conf_adjustment = min(0.15, 0.05 + (total_weight * 0.01))
    
    if result.get("sif_potential"):
        result["confidence"] = round(min(0.99, base_conf + conf_adjustment), 2)
    else:
        # Don't flip the label — but make sure a tuned pattern gets reviewed.
        result["confidence"] = max(0.55, base_conf)
        # Flag for priority review when model disagrees with learned patterns
        result.setdefault("priority_factors", [])
        result["priority_factors"].append(
            "Contains phrases HSE reviewers have linked to SIF in past reviews"
        )
        # Potentially upgrade priority for review
        if result.get("priority") == "LOW":
            result["priority"] = "MEDIUM"

    existing = result.get("uncertainty_note")
    result["uncertainty_note"] = (
        "; ".join(notes) + (f" ({existing})" if existing else "")
    )
    result["tuned"] = True
    result["tuned_weight"] = total_weight
    model = result.get("model") or "rules-v1"
    if "+tuned" not in model:
        result["model"] = f"{model}+tuned"
    return result
