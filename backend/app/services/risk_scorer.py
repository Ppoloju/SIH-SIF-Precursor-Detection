"""AI-assisted prototype priority assessment.

Transparent, configurable scoring used to derive HIGH / MEDIUM / LOW.
This is explicitly NOT an official OIL risk methodology — it requires
HSE validation.

Factors (all derived from the report + matched indicators):
  * matched SIF indicators (count)
  * potential consequence severity (fatality/serious wording)
  * people exposure (actors/actions present)
  * barrier failure (negated indicators or missing-control language)
"""

from app.services.sif_detector import IndicatorMatch, has_exposure

PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"


def _severity_bonus(matches: list[IndicatorMatch]) -> int:
    """Consequences involving fatality get the highest severity weight."""
    for m in matches:
        c = m.consequence.lower()
        if "fatality" in c or "serious injury" in c:
            return 2
    return 1


def _barrier_bonus(matches: list[IndicatorMatch], text: str) -> int:
    if any(m.negated for m in matches):
        return 1
    lower = text.lower()
    missing_terms = ["without", "no ", "missing", "failed", "bypass", "defeat", "not provided", "lack"]
    return 1 if any(t in lower for t in missing_terms) else 0


def assess(
    matches: list[IndicatorMatch], text: str
) -> dict:
    """Return {sif_potential, confidence, priority, priority_factors}."""
    if not matches:
        return {
            "sif_potential": False,
            "confidence": 0.55,
            "priority": PRIORITY_LOW,
            "priority_factors": {"indicators": 0, "severity": 0, "exposure": 0, "barrier_failure": 0},
        }

    n = len(matches)
    severity = _severity_bonus(matches)
    exposure = 1 if has_exposure(text) else 0
    barrier = _barrier_bonus(matches, text)

    # Transparent additive score -> HIGH >= 5, MEDIUM >= 3, else LOW.
    score = min(n, 3) + severity + exposure + barrier
    priority = (
        PRIORITY_HIGH if score >= 5
        else PRIORITY_MEDIUM if score >= 3
        else PRIORITY_LOW
    )
    confidence = round(min(0.97, 0.62 + 0.11 * n + 0.05 * severity), 2)

    return {
        "sif_potential": True,
        "confidence": confidence,
        "priority": priority,
        "priority_factors": {
            "indicators": n,
            "severity": severity,
            "exposure": exposure,
            "barrier_failure": barrier,
        },
    }