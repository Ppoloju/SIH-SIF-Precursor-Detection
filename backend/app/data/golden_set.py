"""Labeled golden evaluation set.

Held-out reference cases used by the evaluation harness (scripts/evaluate.py
and GET /api/evaluation). Every case is a real, report-shaped sentence with an
expert label:

* ``expect_sif``  — does the report carry SIF potential?
* ``expect_rules`` — which canonical Life-Saving Rule(s) should fire?
* ``lang`` — language the report is written in (code used by ``multilingual``
  language detection).

The multilingual cases mirror the vocabulary in
``app/services/multilingual.py`` (romanised + native-script Hindi, Bengali and
Assamese) because that is exactly the phrasing seen on OIL field-reporting
platforms. Keeping the reference set small, explicit and human-checkable is
deliberate: numbers stay trustworthy for a prototype.
"""

from __future__ import annotations

RULE = {
    "energy": "Energy Isolation",
    "confined": "Confined Space Entry",
    "hot_work": "Hot Work Safety",
    "height": "Working at Height",
    "line_of_fire": "Line of Fire",
    "lifting": "Safe Mechanical Lifting",
    "driving": "Driving Safety",
    "toxic": "Toxic Gas Safety",
    "bypass": "Bypassing Safety Controls",
    "permit": "Work Authorization",
}

# Rule key shortcuts used in the case table below.
E = RULE["energy"]
C = RULE["confined"]
HW = RULE["hot_work"]
H = RULE["height"]
LF = RULE["line_of_fire"]
L = RULE["lifting"]
D = RULE["driving"]
T = RULE["toxic"]
B = RULE["bypass"]
P = RULE["permit"]

GOLDEN_CASES: list[dict] = [
    # ------------------------------------------------------------------ en
    {"id": "G-01", "lang": "en", "text": "Two workers entered the storage tank without gas testing and no attendant was posted outside.", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-02", "lang": "en", "text": "The technician started work on a live pipeline without isolating the energy source during maintenance.", "expect_sif": True, "expect_rules": [E]},
    {"id": "G-03", "lang": "en", "text": "Roof workers worked at height without a harness; the scaffold edge had no guardrails.", "expect_sif": True, "expect_rules": [H]},
    {"id": "G-04", "lang": "en", "text": "Welding was carried out without a hot work permit near fuel storage and no fire watch was posted.", "expect_sif": True, "expect_rules": [HW]},
    {"id": "G-05", "lang": "en", "text": "The crane lifted a load beyond its rated capacity with no banksman guiding the lift.", "expect_sif": True, "expect_rules": [L]},
    {"id": "G-06", "lang": "en", "text": "The driver was speeding inside the plant yard and did not follow the speed limit.", "expect_sif": True, "expect_rules": [D]},
    {"id": "G-07", "lang": "en", "text": "The operator entered the sour well area without a gas detector; the H2S alarm was not working.", "expect_sif": True, "expect_rules": [T]},
    {"id": "G-08", "lang": "en", "text": "The mechanic removed the machine guard and defeated the interlock to run the conveyor.", "expect_sif": True, "expect_rules": [B]},
    {"id": "G-09", "lang": "en", "text": "Excavation started without a permit and no shoring was installed near the buried pipeline.", "expect_sif": True, "expect_rules": [P]},
    {"id": "G-10", "lang": "en", "text": "The worker stood directly under the suspended load while the crane was lifting.", "expect_sif": True, "expect_rules": [LF]},
    {"id": "G-11", "lang": "en", "text": "A hose whipped during the pressure test and almost hit the technician standing nearby.", "expect_sif": True, "expect_rules": [LF]},
    {"id": "G-12", "lang": "en", "text": "Entry into the vessel was done without gas testing and the standby man was missing.", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-13", "lang": "en", "text": "After maintenance the valve was left open and pressurised gas released into the area where two mechanics were standing.", "expect_sif": True, "expect_rules": [E]},
    {"id": "G-14", "lang": "en", "text": "A tanker reversed without a spotter at the loading bay and the pedestrian had to step aside quickly.", "expect_sif": True, "expect_rules": [D]},
    {"id": "G-15", "lang": "en", "text": "All crew wore harnesses with proper anchorage; gas tests were done before entry and results were normal.", "expect_sif": False, "expect_rules": []},
    {"id": "G-16", "lang": "en", "text": "One fire extinguisher was found with a missing seal and was replaced on the spot; nobody was exposed.", "expect_sif": False, "expect_rules": []},
    # ------------------------------------------------------------ hi-latn
    {"id": "G-17", "lang": "hi-latn", "text": "Contractor ne bina gas test ke tank ke andar kaam shuru kar diya aur koi attendant nahi tha.", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-18", "lang": "hi-latn", "text": "Technician ne pipeline par kaam shuru kiya bina isolation ke, line pressurize thi.", "expect_sif": True, "expect_rules": [E]},
    {"id": "G-19", "lang": "hi-latn", "text": "Kaam shuru karne se pehle gas detector nahi pehna tha aur area mein h2s ka khatra tha.", "expect_sif": True, "expect_rules": [T]},
    {"id": "G-20", "lang": "hi-latn", "text": "Machine ka guard hata diya aur interlock bypass kar diya tha, phir bhi conveyor chala diya.", "expect_sif": True, "expect_rules": [B]},
    {"id": "G-21", "lang": "hi-latn", "text": "Kaam shuru karne se pehle gas test kiya gaya aur sab kuch normal tha, koi khatra nahi mila.", "expect_sif": False, "expect_rules": []},
    # ------------------------------------------------------------- hi-deva
    {"id": "G-22", "lang": "hi", "text": "टैंक के अंदर प्रवेश गैस टेस्ट के बिना किया गया और कोई अटेंडेंट नहीं था।", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-23", "lang": "hi", "text": "मजदूर ऊंचाई पर बिना हार्नेस के काम कर रहा था और सीढ़ी असुरक्षित थी।", "expect_sif": True, "expect_rules": [H]},
    {"id": "G-24", "lang": "hi", "text": "मशीन की मरम्मत से पहले बिजली बंद नहीं की गई, आइसोलेशन नहीं हुआ।", "expect_sif": True, "expect_rules": [E]},
    {"id": "G-25", "lang": "hi", "text": "वेल्डिंग के समय फायर वॉच नहीं था और ज्वलनशील पदार्थ पास में रखे थे।", "expect_sif": True, "expect_rules": [HW]},
    {"id": "G-26", "lang": "hi", "text": "बिना परमिट के खुदाई शुरू कर दी गई, पास में दबी पाइपलाइन थी।", "expect_sif": True, "expect_rules": [P]},
    {"id": "G-27", "lang": "hi", "text": "कार्य समाप्ति के बाद सभी उपकरण बंद कर दिए गए और क्षेत्र साफ था, कोई समस्या नहीं आई।", "expect_sif": False, "expect_rules": []},
    # ------------------------------------------------------------- bn-deva
    {"id": "G-28", "lang": "bn", "text": "রক্ষণাবেক্ষণের আগে গ্যাস টেস্ট করা হয়নি এবং কোনো অ্যাটেন্ডেন্ট ছিল না, তবুও ট্যাংকে ঢুকেছে।", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-29", "lang": "bn", "text": "পাইপলাইনের কাজ আইসোলেশন ছাড়াই শুরু হয়েছে, লাইনে প্রেশার ছিল।", "expect_sif": True, "expect_rules": [E]},
    {"id": "G-30", "lang": "bn", "text": "হারনেস ছাড়া উঁচু ছাদে কাজ চলছিল, কোনো ফল প্রোটেকশন ছিল না।", "expect_sif": True, "expect_rules": [H]},
    # ------------------------------------------------------------- bn-latn
    {"id": "G-31", "lang": "bn-latn", "text": "Kaj shuru holo gas test chara, tank er vitore dhukar age kono attendant chilo na.", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-32", "lang": "bn-latn", "text": "Crane er operator banksman chara load uthalo, niche kaj korte chilo.", "expect_sif": True, "expect_rules": [L]},
    # ---------------------------------------------------------------- as
    {"id": "G-33", "lang": "as", "text": "টেংকিত সোমোৱাৰ আগত গেছ টেষ্ট নকৰাকৈ কাম আৰম্ভ হৈছিল আৰু এটেণ্ডেণ্ট নাছিল।", "expect_sif": True, "expect_rules": [C]},
    {"id": "G-34", "lang": "as", "text": "হট ৱৰ্ক চলাকালীন ফায়াৰ ৱাচ নাছিল আৰু জ্বলনশীল বস্তু কাষতে আছিল।", "expect_sif": True, "expect_rules": [HW]},
    # ------------------------------------------------------------ as-latn
    {"id": "G-35", "lang": "as-latn", "text": "Perforation job arambh hua permit nai thakote, kono safety check o kora nai.", "expect_sif": True, "expect_rules": [P]},
]

GOLDEN_META = {
    "name": "SIH SIF golden reference set (v1)",
    "total": len(GOLDEN_CASES),
    "note": (
        "Hand-labeled reference cases used to measure SIF-precursor detection and "
        "Life-Saving-Rule mapping, including Hindi / Bengali / Assamese reports. "
        "Verdicts are produced deterministically (no LLM) so results are stable."
    ),
}
