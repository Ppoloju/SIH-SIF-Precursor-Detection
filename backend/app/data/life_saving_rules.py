"""Life-Saving Rule taxonomy seed data.

The taxonomy is configurable: rows are stored in the `life_saving_rules`
table and can be edited/disabled by HSE. Defaults come from the safety
lexicon and require HSE/OIL validation.
"""

from app.services.safety_lexicon import RULES


def rule_seed_rows() -> list[dict]:
    return [
        {
            "name": rule["name"],
            "description": rule["description"],
            "keywords": [i["p"] for i in rule["indicators"]][:50],
            "active": True,
        }
        for rule in RULES
    ]