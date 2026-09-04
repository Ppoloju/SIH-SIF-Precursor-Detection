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
    # Demo seeding disabled - database stays empty for real data only
    logger.info("Demo seeding disabled — database stays empty for real data.")
    return


def seed_all_if_empty(db: Session) -> None:
    seed_rules_if_empty(db)
    seed_demo_if_empty(db)