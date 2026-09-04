"""Safety knowledge base used by the deterministic detection layer.

Single source of truth for:
  * Life-Saving Rule profiles (name, hazard, consequence, barriers, indicators)
  * Generic barrier-failure vocabulary
  * Activity / equipment / exposure vocabularies

Everything here is configurable and requires HSE/OIL validation.
The rule taxonomy can be overridden by rows in the `life_saving_rules` table.
"""

# Tokens that signal a barrier failed / was missing / was bypassed.
NEGATION_TOKENS = [
    "no ",
    "not ",
    "without ",
    "never ",
    "failed ",
    "failure",
    "missing",
    "lack of",
    "bypass",
    "bypassed",
    "defeat",
    "defeated",
    "disabled",
    "removed",
    "did not",
    "didn't",
    "wasn't",
    "unsecured",
    "blocked",
]

# Single-word indicators that must NOT fire when they are only a prefix of
# a larger, unrelated word (e.g. "guard" inside "guardrails" — the rail
# itself is governed by Working at Height, not Bypassing Safety Controls).
FOLLOW_BLOCKS: dict[str, tuple[str, ...]] = {
    "guard": ("rail", "rails", "railings"),
}

# Terms suggesting people are exposed / present near the hazard.
EXPOSURE_TERMS = [
    "worker",
    "workers",
    "technician",
    "crew",
    "operator",
    "driver",
    "electrician",
    "welder",
    "personnel",
    "employee",
    "staff",
    "entered",
    "stood",
    "walked",
    "working",
    "worked",
    "exposed",
    "near",
    "while",
    "during",
    "started",
    "began",
    "hit",
    "struck",
    "near-miss",
    "near miss",
    "incident",
    "almost hit",
    "nearly hit",
    "was present",
    "in the area",
    "on site",
]

# ---------------------------------------------------------------------------
# Life-Saving Rule profiles.
# indicator: {"p": phrase (lowercase), "neg": require a negation token nearby}
# ---------------------------------------------------------------------------
RULES: list[dict] = [
    {
        "name": "Energy Isolation",
        "description": "Verify isolation and ensure zero energy before work begins.",
        "hazard": "Uncontrolled energy",
        "consequence": "Serious injury or fatality from unexpected release of hazardous energy (mechanical, electrical, pressure, thermal)",
        "barriers": ["Energy Isolation / LOTO", "Permit to Work"],
        "follow_up": "Verify isolation and lockout/tagout controls before maintenance begins.",
        "indicators": [
            {"p": "without isolating", "neg": False},
            {"p": "failed to isolate", "neg": False},
            {"p": "did not isolate", "neg": False},
            {"p": "not isolated", "neg": False},
            {"p": "no isolation", "neg": False},
            {"p": "no lockout", "neg": False},
            {"p": "without lockout", "neg": False},
            {"p": "without tagout", "neg": False},
            {"p": "no tagout", "neg": False},
            {"p": "lockout not", "neg": False},
            {"p": "lockout was missing", "neg": False},
            {"p": "loto tag was missing", "neg": False},
            {"p": "bypassed the lockout", "neg": False},
            {"p": "defeated the lockout", "neg": False},
            {"p": "bypassed the isolation", "neg": False},
            {"p": "still energized", "neg": False},
            {"p": "still energised", "neg": False},
            {"p": "without de-energiz", "neg": False},
            {"p": "not de-energiz", "neg": False},
            {"p": "without depressuriz", "neg": False},
            {"p": "not depressuriz", "neg": False},
            {"p": "under pressure", "neg": False},
            {"p": "pressurized", "neg": False},
            {"p": "pressurised", "neg": False},
            {"p": "live line", "neg": False},
            {"p": "live pipeline", "neg": False},
            {"p": "isolat", "neg": True},
            {"p": "lockout", "neg": True},
            {"p": "tagout", "neg": True},
            {"p": "energiz", "neg": True},
            {"p": "de-energiz", "neg": True},
            # Electrical isolation is governed by this same Life-Saving Rule.
            {"p": "live panel", "neg": False},
            {"p": "live wire", "neg": False},
            {"p": "live circuit", "neg": False},
            {"p": "energized circuit", "neg": False},
            {"p": "energised circuit", "neg": False},
            {"p": "without switching off", "neg": False},
            {"p": "not switched off", "neg": False},
            {"p": "exposed live wires", "neg": False},
            {"p": "no barricade", "neg": False},
            {"p": "without barricade", "neg": False},
            {"p": "electrician", "neg": True},
            {"p": "electrical", "neg": True},
            {"p": "circuit", "neg": True},
            {"p": "breaker", "neg": True},
            {"p": "voltage", "neg": True},
            {"p": "rated gloves", "neg": True},
        ],
    },
    {
        "name": "Confined Space Entry",
        "description": "Always obtain authorization and test the atmosphere before entering a confined space.",
        "hazard": "Confined-space hazards (oxygen deficiency, toxic atmosphere)",
        "consequence": "Serious injury or fatality from oxygen deficiency, toxic gas or engulfment",
        "barriers": ["Gas Testing", "Confined-Space Entry Permit", "Standby Attendant", "Rescue Equipment"],
        "follow_up": "Verify atmospheric testing, entry permit, standby attendant and rescue arrangements before confined-space entry.",
        "indicators": [
            {"p": "without gas test", "neg": False},
            {"p": "without gas testing", "neg": False},
            {"p": "no gas test", "neg": False},
            {"p": "no gas testing", "neg": False},
            {"p": "not tested for gas", "neg": False},
            {"p": "no atmospheric test", "neg": False},
            {"p": "oxygen levels", "neg": True},
            {"p": "gas testing", "neg": True},
            {"p": "gas test", "neg": True},
            {"p": "confined space", "neg": True},
            {"p": "entered the tank", "neg": False},
            {"p": "entered the vessel", "neg": False},
            {"p": "tank entry", "neg": False},
            {"p": "vessel entry", "neg": False},
            {"p": "manhole", "neg": True},
            {"p": "standby man", "neg": True},
            {"p": "rescue equipment", "neg": True},
        ],
    },
    {
        "name": "Hot Work Safety",
        "description": "Control flammable materials and ignition sources when performing hot work.",
        "hazard": "Fire / explosion",
        "consequence": "Serious injury or fatality from fire or explosion",
        "barriers": ["Hot-Work Permit", "Fire Watch", "Gas Testing", "Housekeeping / Combustible Control"],
        "follow_up": "Verify hot-work permit, fire watch, gas testing and combustible control before starting hot work.",
        "indicators": [
            {"p": "without hot work permit", "neg": False},
            {"p": "no hot work permit", "neg": False},
            {"p": "hot work", "neg": True},
            {"p": "welding", "neg": True},
            {"p": "welded", "neg": True},
            {"p": "grinding", "neg": True},
            {"p": "sparks", "neg": False},
            {"p": "cutting torch", "neg": False},
            {"p": "oxy-acetylene", "neg": False},
            {"p": "near fuel", "neg": False},
            {"p": "fuel storage", "neg": False},
            {"p": "combustible", "neg": False},
            {"p": "flammable", "neg": False},
            {"p": "hot work permit", "neg": True},
            {"p": "fire watch", "neg": True},
        ],
    },
    {
        "name": "Working at Height",
        "description": "Protect yourself against falls when working at height.",
        "hazard": "Fall from height",
        "consequence": "Serious injury or fatality from a fall from height",
        "barriers": ["Fall Protection", "Scaffolding / Guardrails", "Barricading"],
        "follow_up": "Verify fall protection, edge protection and secure access before working at height.",
        "indicators": [
            {"p": "working at height", "neg": True},
            {"p": "work at height", "neg": True},
            {"p": "without a harness", "neg": False},
            {"p": "without harness", "neg": False},
            {"p": "no harness", "neg": False},
            {"p": "no fall protection", "neg": False},
            {"p": "without fall protection", "neg": False},
            {"p": "lacked guardrails", "neg": False},
            {"p": "no guardrails", "neg": False},
            {"p": "open edge", "neg": False},
            {"p": "open pit", "neg": False},
            {"p": "dropped from", "neg": False},
            {"p": "dropped object", "neg": False},
            {"p": "climbed the ladder", "neg": False},
            {"p": "without anyone holding", "neg": False},
            {"p": "harness", "neg": True},
            {"p": "fall protection", "neg": True},
            {"p": "guardrail", "neg": True},
            {"p": "guard rails", "neg": True},
            {"p": "scaffold", "neg": True},
            {"p": "ladder", "neg": True},
            {"p": "roof", "neg": True},
            {"p": "elevated", "neg": True},
        ],
    },
    {
        "name": "Line of Fire",
        "description": "Keep yourself and others out of the line of fire during operations.",
        "hazard": "Struck-by / line of fire",
        "consequence": "Serious injury or fatality from being struck by moving objects, released energy or dropped loads",
        "barriers": ["Barricading", "Safe Positioning", "Exclusion Zones"],
        "follow_up": "Verify safe positioning and exclusion zones to keep personnel out of the line of fire.",
        "indicators": [
            {"p": "line of fire", "neg": False},
            {"p": "in the path", "neg": False},
            {"p": "under the suspended load", "neg": False},
            {"p": "walked under", "neg": False},
            {"p": "stood under", "neg": False},
            {"p": "near the moving", "neg": False},
            {"p": "while the crane", "neg": False},
            {"p": "whipped", "neg": False},
            {"p": "whipping", "neg": False},
            {"p": "reversing", "neg": False},
            {"p": "pressure test", "neg": False},
            {"p": "blowback", "neg": False},
            {"p": "blew off", "neg": False},
            {"p": "almost hit", "neg": False},
            {"p": "nearly hit", "neg": False},
        ],
    },
    {
        "name": "Safe Mechanical Lifting",
        "description": "Plan lifting operations carefully and control the area to prevent accidents.",
        "hazard": "Suspended load / lifting failure",
        "consequence": "Serious injury or fatality from dropped or uncontrolled loads",
        "barriers": ["Lifting Plan", "Sling Inspection", "Banksman", "Load Chart"],
        "follow_up": "Verify the lifting plan, equipment inspection, load chart and banksman before the lift.",
        "indicators": [
            {"p": "beyond its rated capacity", "neg": False},
            {"p": "overloaded", "neg": False},
            {"p": "no banksman", "neg": False},
            {"p": "without banksman", "neg": False},
            {"p": "raised load", "neg": False},
            {"p": "suspended load", "neg": True},
            {"p": "crane", "neg": True},
            {"p": "sling", "neg": True},
            {"p": "lifting", "neg": True},
            {"p": "lifted", "neg": True},
            {"p": "forklift", "neg": True},
            {"p": "rigging", "neg": True},
            {"p": "hoist", "neg": True},
            {"p": "load chart", "neg": True},
            {"p": "banksman", "neg": True},
        ],
    },
    {
        "name": "Driving Safety",
        "description": "Adhere to safe driving rules to prevent collisions and protect pedestrians.",
        "hazard": "Vehicle collision / pedestrian impact",
        "consequence": "Serious injury or fatality from a vehicle collision or pedestrian impact",
        "barriers": ["Vehicle Controls", "Speed Limits", "Spotter"],
        "follow_up": "Verify vehicle controls, speed limits and pedestrian segregation for vehicle movements.",
        "indicators": [
            {"p": "speeding", "neg": False},
            {"p": "nearly hit the pedestrian", "neg": False},
            {"p": "almost hit the pedestrian", "neg": False},
            {"p": "reversing", "neg": False},
            {"p": "reversed", "neg": False},
            {"p": "without a spotter", "neg": False},
            {"p": "no spotter", "neg": False},
            {"p": "did not follow the speed limit", "neg": False},
            {"p": "tanker", "neg": True},
            {"p": "tanker", "neg": True},
            {"p": "vehicle", "neg": True},
            {"p": "truck", "neg": True},
            {"p": "driver", "neg": True},
            {"p": "pedestrian", "neg": True},
            {"p": "loading bay", "neg": True},
            {"p": "yard", "neg": True},
            {"p": "collision", "neg": True},
            {"p": "blind spot", "neg": True},
        ],
    },
    {
        "name": "Toxic Gas Safety",
        "description": "Monitor air quality and follow procedures when working with toxic gases such as H2S.",
        "hazard": "Toxic gas exposure",
        "consequence": "Serious injury or fatality from toxic gas exposure (e.g. H2S, benzene)",
        "barriers": ["Gas Detector", "Atmospheric Monitoring", "SCBA / Escape Sets", "Wind Direction"],
        "follow_up": "Verify gas detection, monitoring and escape equipment before working where toxic gas may be present.",
        "indicators": [
            {"p": "hydrogen sulfide", "neg": False},
            {"p": "h2s", "neg": False},
            {"p": "sour gas", "neg": False},
            {"p": "sour crude", "neg": False},
            {"p": "toxic gas", "neg": False},
            {"p": "no gas detector", "neg": False},
            {"p": "without gas detector", "neg": False},
            {"p": "gas detector not worn", "neg": False},
            {"p": "no scba", "neg": False},
            {"p": "without breathing apparatus", "neg": False},
            {"p": "benzene exposure", "neg": False},
            {"p": "gas leak", "neg": False},
            {"p": "gas alarm", "neg": False},
            {"p": "h2s alarm", "neg": False},
            {"p": "detector", "neg": True},
            {"p": "breathing apparatus", "neg": True},
            {"p": "gas detector", "neg": True},
            {"p": "gas monitoring", "neg": True},
            {"p": "h2s", "neg": True},
        ],
    },
    {
        "name": "Bypassing Safety Controls",
        "description": "Obtain authorization before overriding or disabling any safety controls.",
        "hazard": "Defeated safety controls",
        "consequence": "Serious injury or fatality from contact with hazards normally controlled by guards or interlocks",
        "barriers": ["Machine Guarding", "Safety Interlocks", "Emergency Stop"],
        "follow_up": "Restore machine guarding, interlocks and emergency-stop controls before resuming work.",
        "indicators": [
            {"p": "bypassed", "neg": False},
            {"p": "defeated the interlock", "neg": False},
            {"p": "guard was removed", "neg": False},
            {"p": "guard was missing", "neg": False},
            {"p": "guard removed", "neg": False},
            {"p": "removed the guard", "neg": False},
            {"p": "interlock was defeated", "neg": False},
            {"p": "emergency stop", "neg": True},
            {"p": "interlock", "neg": True},
            {"p": "machine guard", "neg": True},
            {"p": "guard", "neg": True},
            {"p": "disabled", "neg": True},
        ],
    },
    {
        "name": "Work Authorization",
        "description": "Always work with a valid permit when required.",
        "hazard": "Unauthorized work / missing controls",
        "consequence": "Serious injury or fatality from work performed without required controls",
        "barriers": ["Permit to Work", "Gas Testing", "PTW"],
        "follow_up": "Verify a valid permit to work and required controls before the activity starts.",
        "indicators": [
            {"p": "without permit", "neg": False},
            {"p": "without a permit", "neg": False},
            {"p": "no permit", "neg": False},
            {"p": "without shoring", "neg": False},
            {"p": "no shoring", "neg": False},
            {"p": "without authorisation", "neg": False},
            {"p": "without authorization", "neg": False},
            {"p": "not authorized", "neg": False},
            {"p": "unauthorized work", "neg": False},
            {"p": "unauthorised work", "neg": False},
            {"p": "excavation", "neg": True},
            {"p": "trench", "neg": True},
            {"p": "shoring", "neg": True},
            {"p": "buried", "neg": True},
            {"p": "permit to work", "neg": True},
            {"p": "ptw", "neg": True},
        ],
    },
]

# Rule priority order (used for tie-breaking and dashboard ordering).
RULE_ORDER = [r["name"] for r in RULES]

# ---------------------------------------------------------------------------
# Life-Saving Rule *conditions* — the per-rule requirements the analysis maps
# the report text against ("map out the conditions of the life-saving rule").
#
# Each entry is one requirement/control of the rule:
#   condition : short requirement label shown to the user
#   terms     : control words whose presence in the text = the condition was
#               met — unless a negation / failure word sits nearby, which
#               flips it to "breached".
#   breach    : literal phrases that directly signal the condition failed,
#               even when no control term is present.
#
# Statuses produced by rule_mapper.map_rule_conditions:
#   breached       — the report text shows the requirement was not met
#   in_place       — the report text shows the control was present/applied
#   not_verifiable — the report does not mention this requirement at all
# ---------------------------------------------------------------------------
RULE_CONDITIONS: dict[str, list[dict]] = {
    "Energy Isolation": [
        {
            "condition": "Lockout / tagout (LOTO) applied and locked before work",
            "terms": ["lockout", "tagout", "loto"],
            "breach": ["loto tag was missing", "lockout was missing"],
        },
        {
            "condition": "Energy source isolated and verified at zero energy",
            "terms": ["isolat", "de-energiz", "depressuriz", "switched off", "zero energy"],
            "breach": [
                "without isolating", "failed to isolate", "did not isolate", "not isolated",
                "no isolation", "without isolation", "bypassed the isolation", "still energized",
                "still energised", "without de-energiz", "not de-energiz", "without depressuriz",
                "not depressuriz", "not switched off", "without switching off", "under pressure",
                "pressurized", "pressurised", "energized circuit", "energised circuit",
                "live line", "live pipeline",
            ],
        },
        {
            "condition": "Live-work / line-opening controls and barricading in place",
            "terms": ["barricade", "caution tape", "barrier"],
            "breach": [
                "no barricade", "without barricade", "live wire", "live panel", "live circuit",
                "exposed live wires", "no permit", "without permit",
            ],
        },
    ],
    "Confined Space Entry": [
        {
            "condition": "Atmosphere / gas testing performed before entry",
            "terms": ["gas test", "gas testing", "atmospheric test", "gas monitoring", "oxygen level"],
            "breach": [
                "without gas test", "without gas testing", "no gas test", "no gas testing",
                "not tested for gas", "no atmospheric test",
            ],
        },
        {
            "condition": "Entry authorized (valid confined-space permit)",
            "terms": ["entry permit", "confined space permit", "permit"],
            "breach": ["without permit", "without a permit", "no permit", "not authorized", "without authorisation", "without authorization"],
        },
        {
            "condition": "Standby attendant posted during entry",
            "terms": ["standby man", "standby attendant", "standby person", "attendant", "standby"],
            "breach": ["no attendant", "without attendant", "no standby"],
        },
        {
            "condition": "Rescue / emergency arrangements ready",
            "terms": ["rescue equipment", "rescue plan", "rescue team", "tripod", "winch", "rescue"],
            "breach": ["no rescue equipment", "no rescue plan", "without rescue equipment"],
        },
    ],
    "Hot Work Safety": [
        {
            "condition": "Hot work authorized by permit",
            "terms": ["hot work permit", "welding permit", "permit"],
            "breach": ["without hot work permit", "no hot work permit"],
        },
        {
            "condition": "Fire watch present during hot work",
            "terms": ["fire watch", "firewatcher", "fire watcher"],
            "breach": ["without fire watch", "no fire watch"],
        },
        {
            "condition": "Flammable-vapour / gas testing around the hot work",
            "terms": ["gas test", "gas testing", "flammable test", "combustible gas"],
            "breach": ["without gas test", "no gas test", "no gas testing", "not tested for gas"],
        },
        {
            "condition": "Combustibles kept away from the ignition source",
            "terms": ["housekeeping", "kept clear", "removed combustible"],
            "breach": ["near fuel", "near the fuel", "near flammable", "near combustible", "close to fuel", "sparks", "cutting torch", "oxy-acetylene"],
        },
    ],
    "Working at Height": [
        {
            "condition": "Fall protection (harness / safety line) worn and anchored",
            "terms": ["harness", "fall protection", "safety net", "safety line", "lifeline"],
            "breach": ["without a harness", "without harness", "no harness", "no fall protection", "without fall protection", "safety belt not"],
        },
        {
            "condition": "Edge protection / guardrails in place",
            "terms": ["guardrail", "guard rail", "guardrails", "edge protection", "handrail", "edge"],
            "breach": ["no guardrails", "lacked guardrails", "without guardrails", "open edge", "open pit", "no edge protection"],
        },
        {
            "condition": "Secure, stable access (ladder / scaffold) used",
            # A scaffold/ladder is a *place*, not a control — a failure word in
            # the same clause ("scaffold lacked guardrails") usually refers to
            # a different condition. Breach is only inferred from matched
            # failure phrases / literal anchors, and "in place" needs a
            # positive marker (erected / inspected / …) — mere mention is
            # reported as "not verifiable".
            "presence_breach": False,
            "ok_markers": ["erected", "installed", "inspected", "secured", "stable", "certified", "in place", "well maintained", "complete"],
            "terms": ["scaffold", "scaffolding", "ladder", "work platform"],
            "breach": ["climbed the ladder", "without anyone holding", "unsecured ladder", "ladder not secured", "unsafe ladder", "scaffold collapsed", "ladder fell"],
        },
        {
            "condition": "Work area below barricaded / exclusion zone",
            "terms": ["barricade", "caution tape", "exclusion zone", "safety net"],
            "breach": ["no barricade", "without barricade"],
        },
    ],
    "Line of Fire": [
        {
            "condition": "Personnel kept out of the line of fire",
            "terms": ["exclusion zone", "barricade", "safe position"],
            "breach": ["in the path", "line of fire", "under the suspended load", "walked under", "stood under", "near the moving"],
        },
        {
            "condition": "Movement / lift guided by banksman or spotter",
            "terms": ["banksman", "spotter", "flagman", "signalman"],
            "breach": ["no banksman", "without banksman", "no spotter", "without spotter"],
        },
        {
            "condition": "Energy / pressure release risk controlled (test venting)",
            "terms": ["pressure test", "bleed", "vented", "venting"],
            "breach": ["blowback", "blew off", "whipping", "whipped"],
        },
    ],
    "Safe Mechanical Lifting": [
        {
            "condition": "Lifting plan prepared and followed",
            "terms": ["lifting plan", "lift plan", "method statement"],
            "breach": ["without lifting plan", "no lifting plan"],
        },
        {
            "condition": "Sling / lifting gear in safe condition (inspected)",
            "terms": ["sling", "sling inspection", "certified sling", "shackle", "lifting gear"],
            "breach": ["no sling inspection", "without sling inspection"],
        },
        {
            "condition": "Banksman controls the lift / area cleared",
            "terms": ["banksman", "signalman", "rigger", "spotter"],
            "breach": ["no banksman", "without banksman"],
        },
        {
            "condition": "Load within rated capacity / load chart respected",
            "terms": ["load chart", "rated capacity", "safe working load", "swl"],
            "breach": ["beyond its rated capacity", "overloaded", "exceeded the load chart", "exceeded its capacity"],
        },
    ],
    "Driving Safety": [
        {
            "condition": "Vehicle operated within speed limits",
            "terms": ["speed limit", "speed"],
            "breach": ["speeding", "did not follow the speed limit", "exceeded the speed limit", "above the speed limit", "over the speed limit"],
        },
        {
            "condition": "Reversing / blind-spot movements controlled (spotter)",
            "terms": ["spotter", "mirror", "reversing camera"],
            "breach": ["no spotter", "without a spotter", "without spotter", "reversing blind", "no reversing alarm"],
        },
        {
            "condition": "Pedestrians segregated from vehicle movements",
            "terms": ["pedestrian segregation", "walkway", "pedestrian crossing", "barricade"],
            "breach": ["pedestrian hit", "nearly hit the pedestrian", "almost hit the pedestrian", "vehicle hit the pedestrian", "no pedestrian segregation"],
        },
    ],
    "Toxic Gas Safety": [
        {
            "condition": "Gas detection (H2S / toxic) worn and active",
            "terms": ["gas detector", "h2s detector", "h2s monitor", "gas monitor", "detector"],
            "breach": ["no gas detector", "without gas detector", "gas detector not worn", "no h2s detector", "detector not worn", "detector not working"],
        },
        {
            "condition": "Atmosphere monitored before and during work",
            "terms": ["gas monitoring", "atmospheric monitoring", "gas test", "gas testing", "air monitoring"],
            "breach": ["no gas test", "without gas test", "no monitoring", "not monitored"],
        },
        {
            "condition": "SCBA / escape breathing sets available",
            "terms": ["scba", "breathing apparatus", "escape set", "escape mask", "air pack"],
            "breach": ["no scba", "without scba", "no breathing apparatus", "without breathing apparatus"],
        },
        {
            "condition": "Working position relative to wind considered",
            "terms": ["wind direction", "upwind", "wind sock", "wind"],
            "breach": ["downwind", "working downwind"],
        },
    ],
    "Bypassing Safety Controls": [
        {
            "condition": "Machine guards fitted and in place",
            "terms": ["machine guard", "safety guard", "guard", "guarding"],
            "breach": ["guard was removed", "guard removed", "removed the guard", "guard was missing", "guard missing", "guard was bypassed"],
        },
        {
            "condition": "Safety interlocks operational",
            "terms": ["interlock", "interlocking", "interlock switch"],
            "breach": ["interlock was defeated", "defeated the interlock", "interlock bypassed", "bypassed the interlock", "interlock disabled"],
        },
        {
            "condition": "Emergency stop / isolation controls available",
            "terms": ["emergency stop", "e-stop", "emergency switch", "emergency stop button"],
            "breach": ["emergency stop was bypassed", "emergency stop disabled", "emergency stop removed", "without emergency stop"],
        },
        {
            "condition": "Authorization obtained before overriding controls",
            "terms": ["authorization", "authorisation", "permit"],
            "breach": ["without authorization", "without authorisation", "unauthorized", "unauthorised", "no permit", "without permit"],
        },
    ],
    "Work Authorization": [
        {
            "condition": "Valid permit to work in place before the job starts",
            "terms": ["permit to work", "ptw", "work permit", "permit"],
            "breach": ["without permit", "without a permit", "no permit", "without permit to work", "permit expired", "not authorized", "unauthorized work", "unauthorised work"],
        },
        {
            "condition": "Required gas testing / controls attached to the permit",
            "terms": ["gas test", "gas testing", "atmospheric test"],
            "breach": ["no gas test", "without gas test", "no gas testing"],
        },
        {
            "condition": "Excavation / trench protection (shoring) in place",
            "terms": ["shoring", "trench box", "battering"],
            "breach": ["without shoring", "no shoring", "unshored", "not shored", "cave in", "collapsed"],
        },
    ],
}

# Extra words that mean a control is broken/absent — used by the condition
# mapper's presence check (complement to NEGATION_TOKENS, scoped to rule_mapper).
CONTROL_FAILURE_WORDS = [
    "damaged", "broken", "defective", "collapsed", "expired", "faulty",
    "unstable", "absent", "blocked", "jammed", "corroded", "fell",
    "toppled", "lacked", "lacking", "unsafe", "improper", "not safe",
    "not proper", "not provided", "not installed", "not fitted", "defeated",
]

# Non-English negation words (Hinglish / Banglish / roman Assamese) that sit
# next to an otherwise-English control term and flip its meaning ("harness
# nahi" = no harness). The condition mapper treats these like negation tokens.
FOREIGN_NEGATION_TOKENS = [
    "nahi", "nhi", "bina", "chara", "hoyni", "kora hoyni", "nokori",
    "nokora", "nokorakoi", "nipindha", "nipindhakoi", "nai thakil", "nai",
    "jodi na", "chilo na", "pora hoyni", "hata diya", "khule diye",
]

# Location inference: context word -> canonical work-area label. Used when the
# report never states a location outright but clearly describes one.
LOCATION_TERMS: list[tuple[str, str]] = [
    ("loading bay", "Loading bay"),
    ("control room", "Control room"),
    ("pump room", "Pump room"),
    ("pump house", "Pump room"),
    ("compressor room", "Compressor room"),
    ("compressor house", "Compressor room"),
    ("workshop", "Workshop"),
    ("rooftop", "Roof / elevated work area"),
    ("on the roof", "Roof / elevated work area"),
    ("roof", "Roof / elevated work area"),
    ("scaffolding", "Elevated work area (scaffold)"),
    ("scaffold", "Elevated work area (scaffold)"),
    ("tank farm", "Tank farm"),
    ("storage tank", "Storage tank area"),
    ("inside the tank", "Storage tank area"),
    ("within the tank", "Storage tank area"),
    ("tank", "Storage tank area"),
    ("vessel", "Vessel area"),
    ("manhole", "Confined-space entry point (manhole)"),
    ("pipeline", "Pipeline area"),
    ("piping", "Pipeline area"),
    ("excavation", "Excavation area"),
    ("excavating", "Excavation area"),
    ("trench", "Excavation area (trench)"),
    ("open pit", "Open pit / excavation"),
    ("pit", "Pit / excavation area"),
    ("yard", "Yard"),
    ("access road", "Access road"),
    ("highway", "Public highway"),
    ("road", "Access road"),
    ("jetty", "Jetty / dock"),
    ("wharf", "Jetty / dock"),
    ("dock", "Dock area"),
    ("rig floor", "Rig floor"),
    ("rig site", "Rig site"),
    ("well site", "Well site"),
    ("well pad", "Well pad"),
    ("drilling rig", "Drilling rig area"),
]

# Fallback activity when the report text never says what work was happening but
# the mapped Life-Saving Rule makes the activity obvious.
RULE_TO_ACTIVITY: dict[str, str] = {
    "Energy Isolation": "Isolation / LOTO work",
    "Confined Space Entry": "Confined-space entry",
    "Hot Work Safety": "Hot work",
    "Working at Height": "Working at height",
    "Line of Fire": "Load / equipment movement",
    "Safe Mechanical Lifting": "Lifting operations",
    "Driving Safety": "Driving",
    "Toxic Gas Safety": "Work in a toxic-gas environment",
    "Bypassing Safety Controls": "Machine operation / maintenance",
    "Work Authorization": "Permit-required work",
}

# Generic barrier vocabulary — aggregated into barrier_failure output.
BARRIER_TERMS: dict[str, list[str]] = {
    "Energy Isolation / LOTO": ["loto", "lockout", "tagout", "isolat"],
    "Gas Testing": ["gas test", "gas testing", "atmospheric test"],
    "Permit to Work": ["permit", "ptw", "work authorisation", "work authorization"],
    "Fall Protection": ["harness", "fall protection", "guardrail", "guard rail", "guardrails"],
    "Barricading": ["barricade", "barricading", "barricades", "exclusion zone", "caution tape"],
    "Machine Guarding": ["machine guard", "guard", "guarding", "interlock"],
    "Vehicle Controls": ["spotter", "speed limit", "mirrors"],
    "PPE": ["ppe", "helmet", "gloves", "goggles"],
    "Fire Watch": ["fire watch"],
    "Housekeeping / Combustible Control": ["combustible", "flammable", "housekeeping"],
}

# Extra hazards noticed even when no rule profile matches.
EXTRA_HAZARDS: dict[str, list[str]] = {
    "Fire / explosion": ["fire", "explosion", "explosive", "flammable", "smoke"],
    "Toxic / chemical exposure": ["toxic", "chemical", "hydrogen sulfide", "h2s", "fumes"],
    "High-pressure release": ["high pressure", "high-pressure", "pressure release", "leak"],
    "Moving machinery": ["rotating", "conveyor", "machine", "shaft"],
    "Dropped object": ["dropped", "falling object", "falling tool"],
}

# Activity vocabulary — checked in order, most specific first.
ACTIVITY_TERMS: dict[str, list[str]] = {
    "Confined-space entry": ["confined space", "entered the tank", "entered the vessel", "inside the tank", "within the tank", "tank entry", "vessel entry", "manhole"],
    "Electrical work": ["electrician", "electrical", "live panel", "live wire", "breaker", "circuit", "voltage"],
    "Hot work": ["hot work", "welding", "welded", "weld", "grinding", "torch", "sparks", "oxy-acetylene"],
    "Working at height": ["scaffold", "ladder", "roof", "elevated", "working at height", "work at height", "harness", "height", "open pit"],
    "Lifting operations": ["crane", "forklift", "hoist", "sling", "lifting", "lifted", "rigging", "banksman"],
    "Excavation": ["excavation", "excavating", "trench", "digging", "shoring"],
    "Pipeline work": ["pipeline", "pipe", "flange", "pigging"],
    "Driving": ["driving", "driver", "vehicle", "tanker", "truck", "reversing", "yard", "pedestrian"],
    "Maintenance": ["maintenance", "repair", "overhaul", "servicing", "service", "technician", "mechanic", "job", "machine", "shaft"],
    "Material handling": ["chemical", "drum"],
}

# Equipment vocabulary.
EQUIPMENT_TERMS: dict[str, list[str]] = {
    "Pipeline": ["pipeline", "pipe", "flange", "line"],
    "Pump": ["pump"],
    "Compressor": ["compressor"],
    "Vessel / Tank": ["vessel", "tank"],
    "Crane": ["crane"],
    "Forklift": ["forklift"],
    "Ladder": ["ladder"],
    "Scaffolding": ["scaffold"],
    "Valve": ["valve"],
    "Generator": ["generator"],
    "Boiler": ["boiler"],
    "Drill": ["drill"],
    "Hose": ["hose"],
    "Gas cylinder": ["cylinder"],
    "Electrical panel": ["panel", "breaker", "circuit"],
    "Conveyor": ["conveyor"],
}

# Activity words for classifying a report as unsafe act vs unsafe condition.
ACT_ACTORS = ["worker", "workers", "technician", "crew", "operator", "driver", "electrician", "welder", "employee", "personnel", "contractor"]
CONDITION_WORDS = ["leak", "missing", "damaged", "defective", "exposed", "unguarded", "not provided", "no barricade", "unsecured", "blocked"]

# Phrases that nullify a nearby negation token (positive outcomes must not
# count as barrier failures). Stripped from negation windows before checking.
NULLIFY_PHRASES = [
    "no incident",
    "no incidents",
    "no issue",
    "no issues",
    "no problem",
    "no problems",
    "no hazard",
    "no danger",
    "no injury",
    "no injuries",
    "no damage",
    "no findings",
    "no harm",
    "not reported",
    "no near miss",
]

UNSAFE_ACT = "Unsafe Act"
UNSAFE_CONDITION = "Unsafe Condition"