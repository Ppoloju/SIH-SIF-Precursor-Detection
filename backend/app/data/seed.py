"""Seeding helpers.

* `seed_rules_if_empty` — loads the configurable Life-Saving Rule taxonomy.
* `seed_demo_if_empty` — loads the clearly-labeled synthetic demo dataset
  (each report is analyzed by the real pipeline at seed time so the
  dashboard shows authentic, consistent results).

Demo seeding runs automatically on startup when the database is empty and
`SEED_DEMO_DATA` is not disabled.
"""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.data.demo_reports import demo_report_rows
from app.data.life_saving_rules import rule_seed_rows
from app.models.entities import Analysis, LifeSavingRule, Report
from app.services.analysis_pipeline import analyze_report

logger = logging.getLogger(__name__)


def seed_rules_if_empty(db: Session) -> None:
    if db.query(LifeSavingRule).count() > 0:
        return
    for row in rule_seed_rows():
        db.add(LifeSavingRule(**row))
    db.commit()
    logger.info("Seeded %d Life-Saving Rules", len(rule_seed_rows()))


def seed_demo_if_empty(db: Session) -> None:
    # Honor an explicit opt-out (e.g. a clean/empty database for real data):
    #   SEED_DEMO_DATA=0  -> never insert the synthetic demo rows.
    # Read through Settings so BOTH the environment and backend/.env work.
    settings = get_settings()
    if not settings.seed_demo_data:
        logger.info("Demo seeding disabled — database stays empty for real data.")
        return

    if db.query(Report).count() > 0:
        return

    rows = demo_report_rows()
    for row in rows:
        report = Report(
            report_id=row["report_id"],
            report_text=row["text"],
            report_type=row["report_type"],
            date=row["date"],
            site=row["site"],
            activity=row["activity"],
            is_demo=True,
            source="demo",
        )
        db.add(report)
        db.flush()  # assign id

        try:
            result = analyze_report(row["text"], use_llm=False)
        except Exception as exc:  # noqa: BLE001 — never let seeding fail on one row
            logger.warning("Analysis failed for %s: %s", row["report_id"], exc)
            continue

        db.add(
            Analysis(
                report_id=report.id,
                sif_potential=result["sif_potential"],
                confidence=result["confidence"],
                priority=result["priority"],
                hazard=result["hazard"],
                potential_consequence=result["potential_consequence"],
                barrier_failure=result["barrier_failure"],
                life_saving_rule=result["life_saving_rule"],
                activity=result["activity"],
                evidence=result["evidence"],
                explanation=result["explanation"],
                recommended_follow_up=result["recommended_follow_up"],
                summary=result.get("summary"),
                suggested_actions=result.get("suggested_actions"),
                languages=result.get("languages"),
                uncertainty_note=result.get("uncertainty_note"),
                model=result["model"],
            )
        )
    db.commit()
    logger.info("Seeded %d synthetic demo reports (labeled demo data)", len(rows))


def seed_all_if_empty(db: Session) -> None:
    seed_rules_if_empty(db)
    seed_demo_if_empty(db)