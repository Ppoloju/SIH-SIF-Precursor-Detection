"""Analytics API — aggregated HSE intelligence.

Endpoints: overview, sites, activities, life-saving rules, barriers,
patterns. Metrics are computed from available data only; denominators are
never invented (when unavailable, raw counts are shown and labeled).
"""

import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.db import get_db
from app.models.entities import Analysis, Report
from app.schemas.reports import ReportDetailOut, ReportOut
from app.services import similarity
from app.services.safety_lexicon import RULE_ORDER

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Simple in-memory cache for analytics endpoints
_cache: dict = {}
_TTL_SECONDS = 5  # Cache analytics for 5 seconds

def clear_cache():
    _cache.clear()


def _get_cached(key: str, compute_fn):
    """Get cached result or compute fresh if cache expired."""
    now = time.time()
    if key in _cache and now - _cache[key]["time"] < _TTL_SECONDS:
        return _cache[key]["data"]
    
    data = compute_fn()
    _cache[key] = {"time": now, "data": data}
    return data


def _detail(report: Report, pool: list[dict] | None = None, similar_limit: int = 0) -> ReportDetailOut:
    review = report.reviews[-1] if report.reviews else None
    similar_reports = []
    if pool is not None and similar_limit > 0 and report.analysis:
        similar_reports = similarity.find_similar(
            report=report, pool=[p for p in pool if p["id"] != report.id],
            limit=similar_limit,
        )
    return ReportDetailOut(
        **ReportOut.model_validate(report).model_dump(),
        analysis=report.analysis,
        review=review,
        review_status=review.decision if review else "pending",
        similar_reports=similar_reports,
    )


@router.get("/overview", summary="Dashboard overview KPIs")
def overview(db: Session = Depends(get_db)):
    def _compute_overview():
        # Combine base counts into a single query for better performance
        base_stats = db.execute(
            select(
                func.count(Report.id).label("total"),
                func.count(Analysis.id).filter(Analysis.sif_potential.is_(True)).label("sif_count"),
                func.count(Analysis.id).filter(Analysis.priority == "HIGH").label("high_count"),
                func.count(Report.id).filter(Report.is_demo.is_(True)).label("demo_count"),
                func.max(Report.created_at).label("latest_created")
            )
            .outerjoin(Analysis, Analysis.report_id == Report.id)
        ).first()
        
        total = base_stats.total or 0
        sif_count = base_stats.sif_count or 0
        high_count = base_stats.high_count or 0
        demo_count = base_stats.demo_count or 0
        latest_created = base_stats.latest_created

        top_rule = db.execute(
            select(Analysis.life_saving_rule, func.count(Analysis.id))
            .where(Analysis.life_saving_rule.is_not(None))
            .group_by(Analysis.life_saving_rule)
            .order_by(func.count(Analysis.id).desc())
            .limit(1)
        ).first()

        # Note: grouping by a JSON column is not portable (PostgreSQL has no =
        # operator for `json`), so the top barrier is tallied in Python.
        barrier_counter: Counter = Counter()
        for (barrier_list,) in db.execute(
            select(Analysis.barrier_failure).where(Analysis.barrier_failure.is_not(None))
        ).all():
            for b in barrier_list or []:
                barrier_counter[b] += 1
        top_barrier_name = barrier_counter.most_common(1)[0][0] if barrier_counter else None

        # Optimize trend calculation with single query using fallback date
        report_date_col = func.coalesce(Report.date, func.date(Report.created_at))
        trend_rows = db.execute(
            select(
                report_date_col.label("effective_date"),
                Analysis.sif_potential
            )
            .outerjoin(Analysis, Analysis.report_id == Report.id)
        ).all()

        valid_dates = [r[0] for r in trend_rows if r[0]]
        anchor_date = max(valid_dates) if valid_dates else date.today()
        if isinstance(anchor_date, str):
            anchor_date = date.fromisoformat(anchor_date)
        elif isinstance(anchor_date, datetime):
            anchor_date = anchor_date.date()

        # Build trend map grouped by week start (Monday)
        trend_map = defaultdict(lambda: {"total": 0, "sif_count": 0})
        for r_date, sif_pot in trend_rows:
            if r_date:
                d = r_date if isinstance(r_date, date) else date.fromisoformat(str(r_date)[:10])
                week_start = d - timedelta(days=d.weekday())
                trend_map[week_start]["total"] += 1
                if sif_pot:
                    trend_map[week_start]["sif_count"] += 1

        trend: list[dict] = []
        for week in range(7, -1, -1):
            start = anchor_date - timedelta(days=week * 7)
            week_start = start - timedelta(days=start.weekday())
            data = trend_map.get(week_start, {"total": 0, "sif_count": 0})
            trend.append({"period": start.strftime("%d %b"), "count": data["total"], "sif_count": data["sif_count"]})

        recent = (
            db.execute(
                select(Report)
                .options(selectinload(Report.analysis), selectinload(Report.reviews))
                .join(Analysis, Analysis.report_id == Report.id)
                .where(Analysis.priority == "HIGH")
                .order_by(Report.date.desc().nullslast(), Report.id.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )

        # Mine precursor patterns for overview card
        mined_patterns = _compute_patterns(db)["patterns"]

        # Semantic linking: each recent row carries up to 3 similar past reports
        # so the dashboard can click through to recurrence context immediately.
        recent_pool = None
        if recent and total > 0:
            recent_pool = similarity.pool_rows(db, exclude_id=-1)

        # Data-driven note so the product never claims demo data when the user is
        # looking at (or missing) their own imports.
        if total == 0:
            note = "No reports yet — import your first dataset from the Import Data page and the dashboard fills in live."
        elif demo_count == total:
            note = "All metrics are computed live from the synthetic demo set (labeled in the UI) — import your own dataset anytime."
        elif demo_count:
            note = f"{demo_count} of {total} reports are labeled demo rows; the rest are your imported data."
        else:
            note = "Metrics computed live from your imported dataset."

        return {
            "total_reports": total,
            "sif_potential_reports": sif_count,
            "sif_density": round(100 * sif_count / total, 1) if total else 0.0,
            "high_priority_reports": high_count,
            "top_life_saving_rule": top_rule[0] if top_rule else None,
            "top_barrier_failure": top_barrier_name,
            "trend": trend,
            "recent_high_priority": [
                _detail(r, pool=recent_pool, similar_limit=3) for r in recent
            ],
            "patterns": mined_patterns[:10],
            "latest_report_at": latest_created.isoformat() if latest_created else None,
            "note": note,
        }
    
    return _get_cached("overview", _compute_overview)


@router.get("/life-saving-rules", summary="Life-Saving Rule distribution")
def life_saving_rules(db: Session = Depends(get_db)):
    def _compute_rules():
        # Combine rule distribution and SIF total in single query
        rows = db.execute(
            select(
                Analysis.life_saving_rule,
                func.count(Analysis.id).label('count'),
                func.sum(func.cast(Analysis.sif_potential, Integer)).label('sif_count')
            )
            .where(Analysis.life_saving_rule.is_not(None))
            .group_by(Analysis.life_saving_rule)
            .order_by(func.count(Analysis.id).desc())
        ).all()
        
        counts = {name: {"count": 0, "sif_count": 0} for name in RULE_ORDER}
        for name, count, sif_count in rows:
            if name in counts:
                counts[name] = {"count": count, "sif_count": sif_count or 0}

        sif_total = sum(item["sif_count"] for item in counts.values())
        
        rules = []
        for name in RULE_ORDER:
            count = counts[name]["count"]
            sif_count = counts[name]["sif_count"]
            rules.append(
                {
                    "rule": name,
                    "count": count,
                    "percentage": round(100 * (sif_count or 0) / sif_total, 1) if sif_total else 0.0,
                }
            )
        return {"rules": rules, "sif_total": sif_total, "note": "Percentages are of SIF-potential reports."}
    
    return _get_cached("life_saving_rules", _compute_rules)


@router.get("/sites", summary="Site risk analytics")
def sites(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Report.site, Analysis.hazard, Analysis.life_saving_rule, Analysis.priority)
        .join(Analysis, Analysis.report_id == Report.id)
        .where(Analysis.sif_potential.is_(True), Report.site.is_not(None))
    ).all()

    by_site: dict[str, dict] = {}
    for site, hazard, rule, priority in rows:
        s = by_site.setdefault(
            site, {"site": site, "count": 0, "high": 0, "hazards": Counter(), "rules": Counter()}
        )
        s["count"] += 1
        if priority == "HIGH":
            s["high"] += 1
        if hazard:
            s["hazards"][hazard] += 1
        if rule:
            s["rules"][rule] += 1

    out = []
    for s in by_site.values():
        out.append(
            {
                "site": s["site"],
                "count": s["count"],
                "high": s["high"],
                "main_hazards": [h for h, _ in s["hazards"].most_common(3)],
                "main_rules": [r for r, _ in s["rules"].most_common(3)],
            }
        )
    out.sort(key=lambda x: x["count"], reverse=True)
    return {
        "sites": out,
        "note": "Raw counts shown; a precursor-density denominator is not available, so no density is claimed.",
    }


@router.get("/activities", summary="Activity analytics")
def activities(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Analysis.activity, Analysis.hazard, Analysis.barrier_failure, Analysis.life_saving_rule, Analysis.priority)
        .where(Analysis.sif_potential.is_(True))
    ).all()

    by_act: dict[str, dict] = {}
    for activity, hazard, barriers, rule, priority in rows:
        key = activity or "Not specified"
        a = by_act.setdefault(
            key,
            {
                "activity": key,
                "count": 0,
                "priority": Counter(),
                "hazards": Counter(),
                "barriers": Counter(),
                "rules": Counter(),
            },
        )
        a["count"] += 1
        a["priority"][priority or "LOW"] += 1
        if hazard:
            a["hazards"][hazard] += 1
        for b in barriers or []:
            a["barriers"][b] += 1
        if rule:
            a["rules"][rule] += 1

    out = []
    for a in by_act.values():
        out.append(
            {
                "activity": a["activity"],
                "count": a["count"],
                "priority_distribution": dict(a["priority"]),
                "main_hazards": [h for h, _ in a["hazards"].most_common(3)],
                "main_barriers": [b for b, _ in a["barriers"].most_common(3)],
                "main_rules": [r for r, _ in a["rules"].most_common(3)],
            }
        )
    out.sort(key=lambda x: x["count"], reverse=True)
    return {"activities": out, "note": "Based on SIF-potential reports."}


@router.get("/barriers", summary="Barrier failure analysis")
def barriers(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Analysis.barrier_failure, Report.site, Analysis.activity, Analysis.life_saving_rule, Report.id, Report.report_id)
        .join(Report, Analysis.report_id == Report.id)
        .where(Analysis.barrier_failure.is_not(None))
    ).all()

    by_barrier: dict[str, dict] = defaultdict(
        lambda: {"barrier": "", "count": 0, "sites": Counter(), "activities": Counter(), "rules": Counter(), "examples": []}
    )
    for barrier_list, site, activity, rule, rid, report_id in rows:
        for b in barrier_list or []:
            rec = by_barrier[b]
            rec["barrier"] = b
            rec["count"] += 1
            if site:
                rec["sites"][site] += 1
            if activity:
                rec["activities"][activity] += 1
            if rule:
                rec["rules"][rule] += 1
            if len(rec["examples"]) < 3:
                rec["examples"].append({"id": rid, "report_id": report_id})

    out = []
    for b in by_barrier.values():
        out.append(
            {
                "barrier": b["barrier"],
                "count": b["count"],
                "sites": [s for s, _ in b["sites"].most_common(3)],
                "activities": [a for a, _ in b["activities"].most_common(3)],
                "rules": [r for r, _ in b["rules"].most_common(3)],
                "examples": b["examples"],
            }
        )
    out.sort(key=lambda x: x["count"], reverse=True)
    return {"barriers": out, "note": "Which safety barriers are repeatedly failing."}


def _compute_patterns(db: Session) -> dict:
    rows = db.execute(
        select(
            Analysis.life_saving_rule,
            Analysis.activity,
            Analysis.hazard,
            Analysis.barrier_failure,
            Report.id,
            Report.report_id,
            Report.site,
        )
        .join(Report, Analysis.report_id == Report.id)
        .where(Analysis.sif_potential.is_(True))
    ).all()

    counts: dict[tuple, int] = Counter()
    examples: dict[tuple, list[dict]] = defaultdict(list)

    for rule, activity, hazard, barrier_list, rid, report_id, site in rows:
        if rule and activity:
            key = ("ra", rule, activity)
            counts[key] += 1
            if len(examples[key]) < 3:
                examples[key].append({"id": rid, "report_id": report_id, "site": site})
        if rule and barrier_list:
            for b in barrier_list:
                key = ("rb", rule, b)
                counts[key] += 1
                if len(examples[key]) < 3:
                    examples[key].append({"id": rid, "report_id": report_id, "site": site})
        if hazard and activity:
            key = ("ha", hazard, activity)
            counts[key] += 1
            if len(examples[key]) < 3:
                examples[key].append({"id": rid, "report_id": report_id, "site": site})

    patterns_out: list[dict] = []
    for (kind, a, b), count in counts.most_common():
        if count < 2:
            continue
        if kind == "ra":
            ptype, title, detail, filters = (
                "rule + activity",
                f"{a} during {b.lower()}",
                f"{a} precursors recur during {b.lower()} activities.",
                {"rule": a, "activity": b},
            )
        elif kind == "rb":
            ptype, title, detail, filters = (
                "rule + barrier",
                f"{a} with {b.lower()} failures",
                f"{a} precursors repeatedly involve failed {b.lower()} controls.",
                {"rule": a, "barrier": b},
            )
        else:
            ptype, title, detail, filters = (
                "hazard + activity",
                f"{a} during {b.lower()}",
                f"{a} precursors recur during {b.lower()} activities.",
                {"hazard": a, "activity": b},
            )
        patterns_out.append(
            {
                "type": ptype,
                "title": title,
                "detail": detail,
                "count": count,
                "filters": filters,
                "examples": examples[(kind, a, b)],
            }
        )

    patterns_out.sort(key=lambda p: p["count"], reverse=True)
    return {
        "patterns": patterns_out[:20],
        "note": (
            "Patterns are mined from the actual stored SIF-potential reports; "
            "the counts are real and each pattern links to the reports that "
            "formed it. Nothing is fabricated."
        ),
        "criteria": (
            "Pattern = the same combination of structured fields on >= 2 "
            "SIF-potential reports: Life-Saving Rule + activity, Life-Saving "
            "Rule + barrier failure, or hazard + activity. Click a pattern to "
            "open the real matching reports in the registry."
        ),
    }


@router.get("/patterns", summary="Recurring pattern detection")
def patterns(db: Session = Depends(get_db)):
    """Recurring combinations mined from structured fields of SIF-potential
    reports. Only patterns with >= 2 reports are reported — no fabricated
    patterns. Every pattern carries the *actual* reports that formed it (up to
    3 preview + the total) and the filter link that opens the full set in the
    Reports registry.
    """
    return _compute_patterns(db)