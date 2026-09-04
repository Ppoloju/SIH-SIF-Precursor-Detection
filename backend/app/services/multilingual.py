"""Multilingual detection layer (Hindi / Assamese / Bengali).

OIL safety reports are written mostly in English but frequently mix Hindi
(roman "Hinglish" or Devanagari), Bengali (native or roman "Benglish") and
Assamese. This module lets the deterministic engine understand those reports
the same way it understands English:

* ``detect_foreign_indicators`` — phrase-level entries that map *explicit
  failure phrases* in a non-English language to the same canonical Life-Saving
  Rule, hazard, consequence and barrier profile used for English. Evidence is
  always the literal text found in the original report (never a translation
  the engine invented).
* ``detect_languages`` — which languages/scripts the report uses (script
  ranges for Devanagari / Bengali / Assamese, roman markers for Latin text).

Every entry mirrors the wording actually used on field-reporting platforms
(short, imperative, first-person descriptions). The list is curated and small
on purpose: precision beats recall for an explainable prototype, and HSE can
extend it. The design mirrors ``safety_lexicon`` so rule mapping, analytics and
the Life-Saving-Rule taxonomy stay identical for every language.
"""

from __future__ import annotations

import re

from app.services.safety_lexicon import RULES
from app.services.sif_detector import IndicatorMatch

# Canonical rule name -> profile (hazard / consequence / barriers / description).
_PROFILES: dict[str, dict] = {r["name"]: r for r in RULES}

RULE_ENERGY = "Energy Isolation"
RULE_CONFINED = "Confined Space Entry"
RULE_HOT_WORK = "Hot Work Safety"
RULE_HEIGHT = "Working at Height"
RULE_LINE_OF_FIRE = "Line of Fire"
RULE_LIFTING = "Safe Mechanical Lifting"
RULE_DRIVING = "Driving Safety"
RULE_TOXIC = "Toxic Gas Safety"
RULE_BYPASS = "Bypassing Safety Controls"
RULE_PERMIT = "Work Authorization"

# ---------------------------------------------------------------------------
# Foreign phrase lexicon: language -> rule -> explicit failure phrases.
# Each phrase already carries its "failure" meaning (nahi / bina / chara /
# nokori / না / নাই …), so no extra negation window is required and a matched
# phrase can never mean "everything was fine".
# ---------------------------------------------------------------------------

# --- Hindi — roman script (Hinglish, most common on OIL reporting tools) ---
HI_LATN: dict[str, list[str]] = {
    RULE_ENERGY: [
        "isolation nahi",
        "isolate nahi",
        "bina isolate",
        "bina isolation",
        "lockout nahi",
        "lock nahi laga",
        "tagout nahi",
        "bina lockout",
        "bina depressurize",
        "depressurize nahi",
        "pressure release nahi",
        "switch off nahi",
        "bina switch off",
        "power band nahi",
        "bina power band",
        "still pressurize tha",
    ],
    RULE_CONFINED: [
        "bina gas test",
        "gas test nahi",
        "gas testing nahi",
        "koi gas test",
        "bina gas checking",
        "gas checking nahi",
        "bina attendant",
        "attendant nahi",
        "bina standby",
        "standby nahi",
        "bina gas test ke",
    ],
    RULE_HOT_WORK: [
        "bina hot work permit",
        "hot work permit nahi",
        "bina welding permit",
        "welding permit nahi",
        "bina fire watch",
        "fire watch nahi",
    ],
    RULE_HEIGHT: [
        "bina harness",
        "harness nahi",
        "safety belt nahi",
        "bina safety belt",
        "fall protection nahi",
        "bina fall protection",
        "bina safety net",
    ],
    RULE_LINE_OF_FIRE: [
        "load ke neeche",
        "bhar ke neeche khada",
        "suspended load ke neeche",
        "crane ke neeche",
    ],
    RULE_LIFTING: [
        "bina banksman",
        "banksman nahi",
        "capacity se zyada load",
        "bina lifting plan",
    ],
    RULE_DRIVING: [
        "bina spotter",
        "spotter nahi",
        "speed limit se zyada",
    ],
    RULE_TOXIC: [
        "gas detector nahi",
        "detector nahi pehna",
        "bina gas detector",
        "bina h2s detector",
    ],
    RULE_BYPASS: [
        "guard hata diya",
        "guard remove kar diya",
        "interlock bypass kar diya",
        "bypass kar diya",
        "emergency stop hata diya",
    ],
    RULE_PERMIT: [
        "bina permit",
        "permit nahi",
        "bina ptw",
        "permit ke bina",
        "bina work permit",
        "work permit nahi",
    ],
}

# --- Hindi — Devanagari script ---------------------------------------------
HI_DEVA: dict[str, list[str]] = {
    RULE_ENERGY: [
        "आइसोलेशन नहीं",
        "आइसोलेशन के बिना",
        "बिना आइसोलेशन",
        "लॉकआउट नहीं",
        "बिना लॉकआउट",
        "आइसोलेट नहीं",
        "बिना आइसोलेट",
        "डिप्रेसराइज़ नहीं",
        "बिना डिप्रेसराइज़",
        "स्विच ऑफ नहीं",
        "बिजली बंद नहीं",
    ],
    RULE_CONFINED: [
        "गैस टेस्ट नहीं",
        "गैस टेस्ट के बिना",
        "बिना गैस टेस्ट",
        "गैस जांच नहीं",
        "बिना गैस जांच",
        "अटेंडेंट नहीं",
        "बिना अटेंडेंट",
        "स्टैंडबाय नहीं",
    ],
    RULE_HOT_WORK: [
        "हॉट वर्क परमिट नहीं",
        "बिना हॉट वर्क परमिट",
        "फायर वॉच नहीं",
        "बिना फायर वॉच",
        "वेल्डिंग परमिट नहीं",
    ],
    RULE_HEIGHT: [
        "हार्नेस नहीं",
        "बिना हार्नेस",
        "सेफ्टी बेल्ट नहीं",
        "बिना सेफ्टी बेल्ट",
    ],
    RULE_LINE_OF_FIRE: [
        "लोड के नीचे",
        "भार के नीचे",
    ],
    RULE_LIFTING: [
        "बैंक्समैन नहीं",
        "बिना बैंक्समैन",
    ],
    RULE_DRIVING: [
        "स्पॉटर नहीं",
        "बिना स्पॉटर",
    ],
    RULE_TOXIC: [
        "गैस डिटेक्टर नहीं",
        "बिना गैस डिटेक्टर",
        "डिटेक्टर नहीं",
    ],
    RULE_BYPASS: [
        "गार्ड हटा दिया",
        "इंटरलॉक बायपास",
        "बायपास कर दिया",
    ],
    RULE_PERMIT: [
        "बिना परमिट",
        "परमिट नहीं",
        "बिना अनुमति",
    ],
}

# --- Bengali — native script -------------------------------------------------
BN_DEVA: dict[str, list[str]] = {
    RULE_ENERGY: [
        "আইসোলেশন ছাড়া",
        "আইসোলেশন ছাড়াই",
        "আইসোলেশন করা হয়নি",
        "লকআউট ছাড়া",
        "লকআউট করা হয়নি",
        "প্রেশার রিলিজ ছাড়া",
        "ডিপ্রেসারাইজ করা হয়নি",
        "এনার্জি আইসোলেট করা হয়নি",
    ],
    RULE_CONFINED: [
        "গ্যাস টেস্ট ছাড়া",
        "গ্যাস টেস্ট ছাড়াই",
        "গ্যাস টেস্ট করা হয়নি",
        "গ্যাস পরীক্ষা ছাড়া",
        "অ্যাটেন্ডেন্ট ছিল না",
        "স্ট্যান্ডবাই ছিল না",
        "গ্যাস টেস্ট না করে",
    ],
    RULE_HOT_WORK: [
        "ফায়ার ওয়াচ ছিল না",
        "হট ওয়ার্ক পারমিট ছাড়া",
        "ওয়েল্ডিং পারমিট ছাড়া",
    ],
    RULE_HEIGHT: [
        "হারনেস ছাড়া",
        "সেফটি বেল্ট ছাড়া",
        "ফল প্রোটেকশন ছাড়া",
        "হারনেস পরা ছিল না",
    ],
    RULE_LINE_OF_FIRE: [
        "ঝুলন্ত লোডের নিচে",
        "লোডের নিচে দাঁড়িয়ে",
    ],
    RULE_LIFTING: [
        "ব্যাংকসম্যান ছাড়া",
        "ব্যাংকসম্যান ছিল না",
        "বাইরে লোড চার্ট ছাড়া",
    ],
    RULE_DRIVING: [
        "স্পটার ছাড়া",
        "স্পটার ছিল না",
    ],
    RULE_TOXIC: [
        "গ্যাস ডিটেক্টর ছাড়া",
        "গ্যাস ডিটেক্টর ছিল না",
    ],
    RULE_BYPASS: [
        "গার্ড সরিয়ে দেওয়া",
        "ইন্টারলক বাইপাস",
    ],
    RULE_PERMIT: [
        "পারমিট ছাড়া",
        "পারমিট ছিল না",
    ],
}

# --- Bengali — roman script ("Benglish") --------------------------------------
BN_LATN: dict[str, list[str]] = {
    RULE_ENERGY: [
        "isolation chara",
        "isolation kora hoyni",
        "lockout chara",
        "pressure release chara",
        "depressurize kora hoyni",
        "energize chilo",
    ],
    RULE_CONFINED: [
        "gas test chara",
        "gas test hoyni",
        "gas test kora hoyni",
        "attendant chilo na",
        "standby chilo na",
        "gas test na kore",
    ],
    RULE_HOT_WORK: [
        "fire watch chilo na",
        "hot work permit chara",
        "welding permit chara",
    ],
    RULE_HEIGHT: [
        "harness chara",
        "safety belt chara",
        "harness pore chilo na",
        "fall protection chara",
    ],
    RULE_LINE_OF_FIRE: [
        "load er niche",
        "suspended load er niche",
    ],
    RULE_LIFTING: [
        "banksman chara",
        "banksman chilo na",
        "load chart chara",
    ],
    RULE_DRIVING: [
        "spotter chara",
        "spotter chilo na",
    ],
    RULE_TOXIC: [
        "gas detector chara",
        "detector pora hoyni",
    ],
    RULE_BYPASS: [
        "guard khule diye",
        "interlock bypass kore",
    ],
    RULE_PERMIT: [
        "permit chara",
        "permit chilo na",
    ],
}

# --- Assamese — native script ------------------------------------------------
AS_DEVA: dict[str, list[str]] = {
    RULE_ENERGY: [
        "আইছোলেছন নকৰাকৈ",
        "আইছোলেছন নকৰি",
        "লকআউট নকৰাকৈ",
        "প্ৰেছাৰ ৰিলিজ নকৰাকৈ",
    ],
    RULE_CONFINED: [
        "গেছ টেষ্ট নকৰাকৈ",
        "গেছ টেষ্ট নকৰি",
        "গেছ টেষ্ট কৰা নাছিল",
        "এটেণ্ডেণ্ট নাছিল",
    ],
    RULE_HOT_WORK: [
        "ফায়াৰ ৱাচ নাছিল",
        "হট ৱৰ্ক পাৰ্মিট নাছিল",
    ],
    RULE_HEIGHT: [
        "হাৰ্নেছ নিপিন্ধাকৈ",
        "ছেফটি বেল্ট নিপিন্ধাকৈ",
        "হাৰ্নেছ নাছিল",
    ],
    RULE_LIFTING: [
        "বেংকছমেন নাছিল",
        "বেংকছমেন নকৰাকৈ",
    ],
    RULE_TOXIC: [
        "গেছ ডিটেক্টৰ নাছিল",
        "গেছ ডিটেক্টৰ নিপিন্ধাকৈ",
    ],
    RULE_PERMIT: [
        "পাৰ্মিট নাছিল",
        "পাৰ্মিট অবিহনে",
    ],
}

# --- Assamese — roman script ---------------------------------------------------
AS_LATN: dict[str, list[str]] = {
    RULE_ENERGY: ["isolation nokori", "lockout nokora", "pressure release nokora"],
    RULE_CONFINED: ["gas test nokori", "gas test nokorakoi", "attendant nai thakil", "standby nai"],
    RULE_HOT_WORK: ["fire watch nai thakil", "fire watch nai"],
    RULE_HEIGHT: ["harness nipindhakoi", "harness nai"],
    RULE_TOXIC: ["gas detector nai", "detector nipindha nai"],
    RULE_PERMIT: ["permit nai thakil", "permit nai"],
}

# language key -> {label, script, note}
LANG_META: dict[str, dict[str, str]] = {
    "en": {"label": "English", "script": "Latin", "roman": "0"},
    "hi": {"label": "Hindi", "script": "Devanagari", "roman": "0"},
    "hi-latn": {"label": "Hindi (romanised)", "script": "Latin", "roman": "1"},
    "bn": {"label": "Bengali", "script": "Bengali", "roman": "0"},
    "bn-latn": {"label": "Bengali (romanised)", "script": "Latin", "roman": "1"},
    "as": {"label": "Assamese", "script": "Bengali (Assamese)", "roman": "0"},
    "as-latn": {"label": "Assamese (romanised)", "script": "Latin", "roman": "1"},
}

LANGUAGE_GROUPS: list[dict[str, str | list[str]]] = [
    {"key": "hi", "label": "Hindi", "roman_key": "hi-latn", "lexicons": [HI_DEVA, HI_LATN]},
    {"key": "bn", "label": "Bengali", "roman_key": "bn-latn", "lexicons": [BN_DEVA, BN_LATN]},
    {"key": "as", "label": "Assamese", "roman_key": "as-latn", "lexicons": [AS_DEVA, AS_LATN]},
]

# Roman-script markers used only for *language detection* (which script a
# Latin report was written in). Strong, distinctive tokens.
_ROMAN_MARKERS: dict[str, list[str]] = {
    "hi-latn": [
        "nahi", "kiya", "kiye", "karke", "bina", "shuru", "gaya", "ghus",
        "andar", "upar", "neeche", "hata", "laga", "tha", "hai", "raha",
    ],
    "bn-latn": ["chara", "hoyni", "kora", "kore", "chilo", "na kore", "hoyeche", "dhuke", "khola hoyni"],
    "as-latn": ["nokori", "nokora", "nokorakoi", "nipindhakoi", "nai thakil", "thakil", "hole"],
}

_DEVA_RANGE = range(0x0900, 0x0980)
_BENGALI_RANGE = range(0x0980, 0x0A00)
_AS_CHARS = {0x09F0, 0x09F1}  # ৰ / ৱ — Assamese-only letters


_NEUTRAL_CHARS = {0x0964, 0x0965}  # danda / double-danda shared by many Indic scripts


def detect_languages(text: str) -> list[str]:
    """Which languages/scripts appear in the report (ordered)."""
    if not text:
        return []
    found: list[str] = []
    has_latin = any(ch.isascii() and ch.isalpha() for ch in text)

    def _has_script(code: str) -> bool:
        for ch in text:
            o = ord(ch)
            if o in _NEUTRAL_CHARS:
                continue  # danda punctuation is shared across scripts
            if code == "hi" and o in _DEVA_RANGE:
                return True
            if code in ("bn", "as") and o in _BENGALI_RANGE:
                return True
        return False

    if _has_script("hi"):
        found.append("hi")
    if _has_script("bn") or _has_script("as"):
        # ৰ / ৱ are Assamese-only letters within the shared Bengali block.
        ascript = any(ord(ch) in _AS_CHARS for ch in text)
        found.append("as" if ascript else "bn")

    if has_latin:
        found.append("en")
        # Tokenise loosely (punctuation -> spaces) so marker words are found
        # even when followed by a comma or full stop.
        lower = re.sub(r"[^a-z0-9 ]", " ", text.lower())
        lower = f" {lower} "
        for roman_key, markers in _ROMAN_MARKERS.items():
            hits = sum(1 for m in markers if f" {m} " in lower)
            base = roman_key.split("-")[0]
            # Skip roman label when the native script is already detected or
            # when the markers are too few (an English sentence can contain
            # isolated borrowed words like "nahi" rarely — require >= 2).
            if hits >= 2 and base not in found:
                found.append(roman_key)
    return found


def label_for(lang_code: str) -> str:
    meta = LANG_META.get(lang_code)
    return meta["label"] if meta else lang_code


# ---------------------------------------------------------------------------
# Phrase matching
# ---------------------------------------------------------------------------

def _iter_patterns() -> list[tuple[str, str, list[str]]]:
    """(language_code, rule, patterns) for every non-Latin lexicon entry."""
    for group in LANGUAGE_GROUPS:
        for lexicon in group["lexicons"]:  # type: ignore[attr-defined]
            for rule, patterns in lexicon.items():
                yield group["key"], rule, patterns  # type: ignore[union-attr]


def _all_patterns_by_rule() -> dict[str, list[tuple[str, str]]]:
    """rule -> [(lang_code, phrase)] across every language."""
    out: dict[str, list[tuple[str, str]]] = {}
    for lang_code, rule, patterns in _iter_patterns():
        for phrase in patterns:
            out.setdefault(rule, []).append((lang_code, phrase))
    return out


def _expand_evidence(text: str, start: int, end: int) -> str:
    """Widen to natural token boundaries for clean evidence quotes."""
    strip_chars = " \t\n.,;:!?()[]{}'\"|«»“”‘’—–"
    s, e = start, end
    while s > 0 and text[s - 1] not in strip_chars:
        s -= 1
    while e < len(text) and text[e] not in strip_chars:
        e += 1
    return text[s:e].strip()


def detect_foreign_indicators(text: str) -> list[IndicatorMatch]:
    """Return matches for non-English failure phrases, if any."""
    if not text or not text.strip():
        return []
    haystack = text.lower()
    matches: list[IndicatorMatch] = []
    seen_ranges: list[tuple[str, int, int]] = []  # (rule, start, end)

    for lang_code, rule, patterns in _iter_patterns():
        profile = _PROFILES.get(rule)
        if profile is None:
            continue
        for phrase in patterns:
            pos = haystack.find(phrase)
            if pos == -1:
                continue
            # skip if the same rule already matched this exact spot
            if any(r == rule and not (pos >= e or pos + len(phrase) <= s) for r, s, e in seen_ranges):
                continue
            evidence = _expand_evidence(text, pos, pos + len(phrase))
            seen_ranges.append((rule, pos, pos + len(phrase)))
            matches.append(
                IndicatorMatch(
                    rule=rule,
                    phrase=evidence,
                    start=pos,
                    end=pos + len(phrase),
                    hazard=profile["hazard"],
                    consequence=profile["consequence"],
                    barriers=list(profile["barriers"]),
                    negated=True,  # the phrase itself expresses the failure
                )
            )
    matches.sort(key=lambda m: (m.start, -len(m.phrase)))
    return matches


# Equipment vocabulary in foreign languages (merged into extraction).
FOREIGN_EQUIPMENT: dict[str, dict[str, list[str]]] = {
    "Pipeline": ["पाइपलाइन", "পাইপলাইন", "পাইপলাইনখন", "पाइप", "পাইপ"],
    "Vessel / Tank": ["टैंक", "टंकी", "ট্যাংক", "টেংকি", "টেংক", "টাংকি"],
    "Crane": ["क्रेन", "ক্রেন", "ক্ৰেন"],
    "Ladder": ["सीढ़ी", "सिढी", "মই", "মইখন", "সিড়ি"],
    "Scaffolding": ["स्कैफोल्ड", "স্ক্যাফোল্ডিং", "স্কাফল্ডিং"],
    "Generator": ["जनरेटर", "জেনারেটর"],
    "Valve": ["वाल्व", "ভালভ"],
    "Hose": ["होज़", "হোস", "পাইপ"],
    "Electrical panel": ["पैनल", "প্যানেল"],
    "Pump": ["पंप", "পাম্প"],
}


def foreign_equipment(text: str) -> list[str]:
    found: list[str] = []
    for name, terms in FOREIGN_EQUIPMENT.items():
        if any(t in text for t in terms):
            found.append(name)
    return found


def rules_foreign_only(text: str) -> list[str]:
    """Rules that appear only via non-English phrases (for provenance)."""
    english_rules = {m.rule for m in _en_matches_for(text)}
    foreign_rules = {m.rule for m in detect_foreign_indicators(text)}
    return sorted(foreign_rules - english_rules)


def _en_matches_for(text: str) -> list[IndicatorMatch]:
    from app.services.sif_detector import detect_indicators  # local import to avoid a cycle at module load

    return detect_indicators(text)
