"""Synthetic demo dataset.

IMPORTANT: All reports in this file are SYNTHETIC and invented for
demonstration and development. They are NOT actual OIL reports. Each report
is flagged `is_demo=True` in the database and the UI shows a
"Demo / Synthetic Data" label.

`expected_sif` / `expected_rule` are used only by the evaluation harness
(Phase 17) — they are never exposed through the API.
"""

from datetime import date, timedelta

# (report_type, site, activity, days_ago, text, expected_sif, expected_rule)
DEMO_REPORTS: list[tuple[str, str, str, int, str, bool, str | None]] = [
    # --- Energy Isolation (recurring: maintenance) ---
    ("Unsafe Act", "Site A — Pipeline Terminal", "Maintenance", 14,
     "During maintenance, the technician started work on a pipeline without properly isolating the energy source.", True, "Energy Isolation"),
    ("Unsafe Act", "Site B — Processing Plant", "Maintenance", 10,
     "Worker began servicing the pump while it was still energized; the LOTO tag was missing.", True, "Energy Isolation"),
    ("Unsafe Act", "Site C — Drilling Rig", "Maintenance", 6,
     "A contractor bypassed the lockout on the compressor to save time and started the job.", True, "Energy Isolation"),
    ("Unsafe Condition", "Site A — Pipeline Terminal", "Maintenance", 3,
     "The crew isolated and depressurized the pipeline before maintenance began; LOTO was applied and verified.", False, "Energy Isolation"),
    # --- Confined Space (recurring: missing gas testing) ---
    ("Unsafe Act", "Site B — Processing Plant", "Confined-space entry", 12,
     "Two workers entered the storage tank without gas testing and no attendant was posted.", True, "Confined Space"),
    ("Unsafe Act", "Site B — Processing Plant", "Confined-space entry", 8,
     "Crew entered the vessel without checking oxygen levels; rescue equipment was not available.", True, "Confined Space"),
    ("Unsafe Condition", "Site D — Refinery Unit", "Confined-space entry", 4,
     "Confined space entry was performed with a valid permit, a working gas monitor and a standby man present.", False, "Confined Space"),
    # --- Working at Height (recurring: missing fall protection) ---
    ("Unsafe Act", "Site E — Field Depot", "Working at height", 11,
     "Roof worker was seen working at height without a harness and the scaffold lacked guardrails.", True, "Working at Height"),
    ("Unsafe Act", "Site B — Processing Plant", "Working at height", 7,
     "Technician climbed the ladder to repair the light without anyone holding the ladder; the ladder was damaged.", True, "Working at Height"),
    ("Unsafe Condition", "Site C — Drilling Rig", "Working at height", 2,
     "Fall protection was worn and anchor points inspected before elevated work on the platform.", False, "Working at Height"),
    # --- Hot Work (recurring: permit / fire watch) ---
    ("Unsafe Act", "Site A — Pipeline Terminal", "Hot work", 13,
     "Welding was started near the fuel storage area without a hot work permit and no fire watch.", True, "Hot Work"),
    ("Unsafe Condition", "Site D — Refinery Unit", "Hot work", 9,
     "Grinding sparks fell onto oily rags; the area was not cleared of combustibles before hot work.", True, "Hot Work"),
    ("Unsafe Condition", "Site E — Field Depot", "Hot work", 5,
     "Hot work was performed with a permit, a fire watch and extinguishers positioned at the site.", False, "Hot Work"),
    # --- Line of Fire ---
    ("Unsafe Act", "Site A — Pipeline Terminal", "Pipeline work", 16,
     "A worker stood directly in the line of fire while the pressure test was being released.", True, "Line of Fire"),
    ("Unsafe Act", "Site C — Drilling Rig", "Lifting operations", 10,
     "Operator walked under the suspended load while the crane was moving the pipe spool.", True, "Line of Fire"),
    ("Unsafe Act", "Site E — Field Depot", "Driving", 6,
     "Employees stood in the path of the reversing tanker in the loading bay.", True, "Line of Fire"),
    # --- Lifting Operations ---
    ("Unsafe Act", "Site C — Drilling Rig", "Lifting operations", 15,
     "Crane lifted the load beyond its rated capacity; the sling angle was unsafe and no banksman was present.", True, "Lifting Operations"),
    ("Unsafe Act", "Site B — Processing Plant", "Lifting operations", 9,
     "Forklift carried a raised load through the workshop with the load blocking the driver's view.", True, "Lifting Operations"),
    ("Unsafe Condition", "Site C — Drilling Rig", "Lifting operations", 3,
     "Rigging was inspected and the load chart verified before the lift; banksman was in position.", False, "Lifting Operations"),
    # --- Driving ---
    ("Unsafe Act", "Site E — Field Depot", "Driving", 17,
     "Tanker driver was speeding through the yard and nearly hit the pedestrian crossing.", True, "Driving"),
    ("Unsafe Act", "Site E — Field Depot", "Driving", 8,
     "Vehicle reversed without a spotter near the parked trailers; mirrors were not used.", True, "Driving"),
    ("Unsafe Condition", "Site E — Field Depot", "Driving", 1,
     "Driver followed the yard speed limit and used the designated route; no incidents reported.", False, "Driving"),
    # --- Electrical ---
    ("Unsafe Act", "Site B — Processing Plant", "Electrical work", 18,
     "Electrician worked on a live panel without switching off the circuit or wearing rated gloves.", True, "Electrical Isolation"),
    ("Unsafe Condition", "Site D — Refinery Unit", "Electrical work", 7,
     "Exposed live wires were found near the work area with no barricade or warning sign.", True, "Electrical Isolation"),
    ("Unsafe Condition", "Site B — Processing Plant", "Electrical work", 2,
     "Electrical job was done under permit with the circuit isolated and tested dead before work.", False, "Electrical Isolation"),
    # --- Bypassing Safety Controls / guards ---
    ("Unsafe Condition", "Site D — Refinery Unit", "Hot work", 5,
     "Gas cylinder left unsecured next to the welding area without a chain or warning sign.", True, "Hot Work"),
    ("Unsafe Condition", "Site B — Processing Plant", "Maintenance", 12,
     "Machine guard was removed from the conveyor and the interlock was defeated.", True, "Bypassing Safety Controls"),
    ("Unsafe Condition", "Site B — Processing Plant", "Maintenance", 6,
     "The emergency stop button was blocked by material; the machine could not be stopped quickly.", True, "Bypassing Safety Controls"),
    ("Incident", "Site B — Processing Plant", "Maintenance", 8,
     "Incident: worker's hand contacted the rotating shaft; the guard was missing.", True, "Bypassing Safety Controls"),
    # --- Work Authorisation / excavation ---
    ("Unsafe Act", "Site A — Pipeline Terminal", "Excavation", 14,
     "Excavation was dug without shoring near the buried gas line; no permit was issued.", True, "Work Authorisation"),
    ("Unsafe Condition", "Site A — Pipeline Terminal", "Working at height", 4,
     "Barricading was removed around the open pit; a worker walked near the unprotected edge.", True, "Working at Height"),
    # --- Pressure / line of fire ---
    ("Unsafe Condition", "Site D — Refinery Unit", "Maintenance", 9,
     "High-pressure hose coupling failed during cleaning and whipped around; a nearby worker was almost hit.", True, "Line of Fire"),
    ("Unsafe Act", "Site A — Pipeline Terminal", "Pipeline work", 5,
     "Operator opened the pressure line without depressurizing it; the fitting blew off.", True, "Energy Isolation"),
    ("Near Miss", "Site A — Pipeline Terminal", "Maintenance", 3,
     "Near-miss: flange coupling slipped while the line was still pressurized; no injury reported.", True, "Energy Isolation"),
    # --- Mixed / non-SIF variety ---
    ("Unsafe Condition", "Site D — Refinery Unit", "Maintenance", 5,
     "Defective pressure gauge was replaced after inspection flagged the damage before use.", False, None),
    ("Unsafe Act", "Site E — Field Depot", "Material handling", 7,
     "Worker handled the chemical drum without wearing the required gloves; PPE was missing.", False, None),
    ("Near Miss", "Site C — Drilling Rig", "Working at height", 6,
     "Near-miss: a falling tool dropped from the scaffold landing area; barricade was missing below.", True, "Working at Height"),
    ("Unsafe Condition", "Site B — Processing Plant", "Operations", 3,
     "Smoke was observed from the compressor area during the night shift; the source was not immediately located.", False, None),
    ("Unsafe Condition", "Site E — Field Depot", "Material handling", 11,
     "Tanker overfilled and diesel spilled on the ground near the drain; bunding was not provided.", False, None),
    ("Unsafe Act", "Site B — Processing Plant", "Confined-space entry", 13,
     "Worker was welding inside the tank without ventilation and no gas test was done.", True, "Confined Space"),
    ("Unsafe Act", "Site E — Field Depot", "Driving", 4,
     "The driver did not follow the speed limit inside the terminal and skipped the pre-drive check.", True, "Driving"),
    ("Unsafe Act", "Site C — Drilling Rig", "Lifting operations", 2,
     "The crane operator lowered the load onto the truck without a banksman guiding the swing.", True, "Lifting Operations"),
    ("Unsafe Condition", "Site D — Refinery Unit", "Hot work", 7,
     "Oily rags and empty drums were left near the welding station; combustible material close to ignition source.", True, "Hot Work"),
    ("Unsafe Condition", "Site E — Field Depot", "Operations", 1,
     "Housekeeping issue: tools left on the walkway; the area was cleaned after the shift.", False, None),
    ("Unsafe Act", "Site B — Processing Plant", "Electrical work", 1,
     "Worker replaced the light bulb on the live circuit without using insulated tools.", True, "Electrical Isolation"),
]


def demo_date(offset_days: int, today: date | None = None) -> date:
    return (today or date.today()) - timedelta(days=offset_days)


def demo_report_rows() -> list[dict]:
    today = date.today()
    return [
        {
            "report_id": f"RPT-{i + 1:04d}",
            "report_type": report_type,
            "site": site,
            "activity": activity,
            "date": demo_date(days_ago, today),
            "text": text,
            "expected_sif": expected_sif,
            "expected_rule": expected_rule,
        }
        for i, (report_type, site, activity, days_ago, text, expected_sif, expected_rule) in enumerate(DEMO_REPORTS)
    ]