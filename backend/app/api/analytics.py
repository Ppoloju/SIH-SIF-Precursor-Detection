"""Analytics API — aggregated HSE intelligence.

Endpoints: overview, sites, activities, life-saving rules, barriers,
patterns. Metrics are computed from available data only; denominators are
never invented (when unavailable, raw counts are shown and labeled).
"""

from collections import Counter, defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.db import get_db
from app.models.entities import Analysis, Report
from app.schemas.reports import ReportDetailOut, ReportOut
from app.services import similarity

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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
    total = db.scalar(select(func.count(Report.id))) or 0
    sif_count = (
        db.scalar(select(func.count(Analysis.id)).where(Analysis.sif_potential.is_(True))) or 0
    )
    high_count = (
        db.scalar(select(func.count(Analysis.id)).where(Analysis.priority == "HIGH")) or 0
    )

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

    today = date.today()
    trend: list[dict] = []
    for week in range(8, 0, -1):
        start = today - timedelta(days=week * 7)
        end = today - timedelta(days=(week - 1) * 7)
        total_w = (
            db.scalar(select(func.count(Report.id)).where(Report.date >= start, Report.date < end))
            or 0
        )
        sif_w = (
            db.scalar(
                select(func.count(Analysis.id))
                .join(Report, Analysis.report_id == Report.id)
                .where(Analysis.sif_potential.is_(True), Report.date >= start, Report.date < end)
            )
            or 0
        )
        trend.append({"period": start.strftime("%d %b"), "count": total_w, "sif_count": sif_w})

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

    # Semantic linking: each recent row carries up to 3 similar past reports
    # so the dashboard can click through to recurrence context immediately.
    recent_pool = None
    if recent and total > 0:
        recent_pool = similarity.pool_rows(db, exclude_id=-1)

    latest_created = db.scalar(select(func.max(Report.created_at)))
    demo_count = (
        db.scalar(select(func.count(Report.id)).where(Report.is_demo.is_(True))) or 0
    )

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
        "patterns": [],
        "latest_report_at": latest_created.isoformat() if latest_created else None,
        "note": note,
    }


@router.get("/life-saving-rules", summary="Life-Saving Rule distribution")
def life_saving_rules(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Analysis.life_saving_rule, func.count(Analysis.id))
        .where(Analysis.life_saving_rule.is_not(None))
        .group_by(Analysis.life_saving_rule)
        .order_by(func.count(Analysis.id).desc())
    ).all()
    sif_total = (
        db.scalar(select(func.count(Analysis.id)).where(Analysis.sif_potential.is_(True))) or 0
    )
    rules = []
    for name, count in rows:
        rules.append(
            {
                "rule": name,
                "count": count,
                "percentage": round(100 * count / sif_total, 1) if sif_total else 0.0,
            }
        )
    return {"rules": rules, "sif_total": sif_total, "note": "Percentages are of SIF-potential reports."}


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


@router.get("/patterns", summary="Recurring pattern detection")
def patterns(db: Session = Depends(get_db)):
    """Recurring combinations mined from structured fields.

    Only patterns with >= 2 reports are reported — no fabricated patterns.
    """
    rows = db.execute(
        select(Analysis.life_saving_rule, Analysis.activity, Analysis.hazard, Analysis.barrier_failure)
        .join(Report, Analysis.report_id == Report.id)
        .where(Analysis.sif_potential.is_(True))
    ).all()

    rule_activity: Counter = Counter()
    rule_barrier: Counter = Counter()
    hazard_activity: Counter = Counter()
    for rule, activity, hazard, barrier_list in rows:
        if rule and activity:
            rule_activity[(rule, activity)] += 1
        if rule and barrier_list:
            for b in barrier_list:
                rule_barrier[(rule, b)] += 1
        if hazard and activity:
            hazard_activity[(hazard, activity)] += 1

    patterns_out: list[dict] = []
    for (rule, activity), count in rule_activity.most_common():
        if count >= 2:
            patterns_out.append(
                {
                    "type": "rule + activity",
                    "title": f"{rule} during {activity.lower()}",
                    "detail": f"{rule} precursors recur during {activity.lower()} activities.",
                    "count": count,
                }
            )
    for (rule, barrier), count in rule_barrier.most_common():
        if count >= 2:
            patterns_out.append(
                {
                    "type": "rule + barrier",
                    "title": f"{rule} with {barrier.lower()} failures",
                    "detail": f"{rule} precursors repeatedly involve failed {barrier.lower()} controls.",
                    "count": count,
                }
            )
    for (hazard, activity), count in hazard_activity.most_common():
        if count >= 2:
            patterns_out.append(
                {
                    "type": "hazard + activity",
                    "title": f"{hazard} during {activity.lower()}",
                    "detail": f"{hazard} precursors recur during {activity.lower()} activities.",
                    "count": count,
                }
            )
    return {
        "patterns": patterns_out[:20],
        "note": "Patterns are mined from available structured data; none are fabricated.",
    }