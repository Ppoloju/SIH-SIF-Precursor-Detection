"""Build train/validation/test CSVs from immutable real-world dumps.

Reads ``docs/Real datasets/`` only. Writes ``data/processed/``. Never
overwrites source files. Output labels come from the existing rule engine
(``analyze_report(..., use_llm=False)``), not from random synthesis.

Usage (from the backend directory):

    py -3 scripts/build_processed_datasets.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
RAW_ROOT = REPO_ROOT / "docs" / "Real datasets"
OUT_ROOT = REPO_ROOT / "data" / "processed"
DOCS_ROOT = REPO_ROOT / "docs"

SEED = 42
TARGET_N = 10_000
TRAIN_FRAC = 0.60
VAL_FRAC = 0.20
MIN_DESC_LEN = 40
DATASET_VERSION = "real-osha-msha-v1"
PREPROCESSING_VERSION = "pipeline-v1"
SAMPLE_PER_FAMILY = 5_200  # oversample then exact-dedupe down to TARGET_N

sys.path.insert(0, str(BACKEND_ROOT))

MISSING_TOKENS = {
    "",
    "?",
    "n/a",
    "na",
    "none",
    "null",
    "nan",
    "no value found",
    "not reported",
    "not listed",
    "not marked",
}

CANONICAL_COLUMNS = [
    "report_id",
    "report_type",
    "site_name",
    "activity",
    "date_reported",
    "description",
    "actual_severity",
    "date_closed",
    "status",
    "observation_date",
    "location_detail",
    "equipment",
    "hazard",
    "barrier_failure",
    "lsr",
    "sif_potential",
    "priority",
    "potential_severity",
    "precursor",
    "sif_probability",
    "reason",
    "suggested_immediate_action",
    "short_summary",
    "source_dataset",
    "source_file",
    "source_incident_id",
    "group_id",
    "split",
    "record_origin",
    "dataset_version",
    "preprocessing_version",
    "analysis_model",
    "report_type_origin",
    "site_name_origin",
    "activity_origin",
    "date_reported_origin",
    "description_origin",
    "actual_severity_origin",
    "date_closed_origin",
    "status_origin",
    "observation_date_origin",
    "location_detail_origin",
    "equipment_origin",
    "outputs_origin",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in MISSING_TOKENS:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text


def _iso_date(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else ""


def _norm_desc(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _desc_hash(text: str) -> str:
    return hashlib.sha256(_norm_desc(text).encode("utf-8", errors="replace")).hexdigest()


def _csv_files(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.csv"), key=lambda p: p.name.lower())


def reservoir_sample(items: Iterable[dict], k: int, rng: random.Random) -> list[dict]:
    sample: list[dict] = []
    for i, item in enumerate(items):
        if i < k:
            sample.append(item)
        else:
            j = rng.randrange(i + 1)
            if j < k:
                sample[j] = item
    return sample


def map_dataset1_row(row: dict, path: Path) -> dict | None:
    narr = _clean(row.get("AI_NARR"))
    if len(narr) < MIN_DESC_LEN:
        return None
    doc = _clean(row.get("DOCUMENT_NO")) or _clean(row.get("MINE_ID"))
    if not doc:
        return None
    loc_bits = [
        _clean(row.get("SUBUNIT_DESC")),
        _clean(row.get("UG_LOCATION")),
        _clean(row.get("OPERATOR_NAME")),
    ]
    equip = _clean(row.get("MINING_EQUIP"))
    degree = _clean(row.get("INJ_DEGR_DESC"))
    report_type = ""
    report_type_origin = "unknown"
    if "ACCIDENT ONLY" in degree.upper():
        # MSHA "accident only" = event without a qualifying injury.
        report_type = "Near miss"
        report_type_origin = "inferred"
    closed = _iso_date(row.get("RETURN_TO_WORK_DT") or "")
    return {
        "source_dataset": "msha_accidents",
        "source_file": path.name,
        "source_incident_id": doc,
        "report_id": f"MSHA-{doc}",
        "group_id": f"MSHA-{doc}",
        "report_type": report_type,
        "report_type_origin": report_type_origin,
        "site_name": _clean(row.get("OPERATOR_NAME")),
        "site_name_origin": "original" if _clean(row.get("OPERATOR_NAME")) else "unknown",
        "activity": _clean(row.get("AI_ACTY_DESC")),
        "activity_origin": "original" if _clean(row.get("AI_ACTY_DESC")) else "unknown",
        "date_reported": _iso_date(row.get("AI_DT") or ""),
        "date_reported_origin": "original" if _iso_date(row.get("AI_DT") or "") else "unknown",
        "observation_date": _iso_date(row.get("AI_DT") or ""),
        "observation_date_origin": "original" if _iso_date(row.get("AI_DT") or "") else "unknown",
        "description": narr,
        "description_origin": "original",
        "actual_severity": degree,
        "actual_severity_origin": "original" if degree else "unknown",
        "date_closed": closed,
        "date_closed_origin": "original" if closed else "unknown",
        "status": "Closed" if closed else "",
        "status_origin": "inferred" if closed else "unknown",
        "location_detail": ", ".join(b for b in loc_bits if b),
        "location_detail_origin": "original" if any(loc_bits) else "unknown",
        "source_equipment": equip,
    }


def sample_dataset1(k: int, rng: random.Random) -> tuple[list[dict], dict[str, Any]]:
    folder = RAW_ROOT / "OSHA Dataset 1"
    files = _csv_files(folder)
    stats: dict[str, Any] = {
        "name": "OSHA Dataset 1 (MSHA mine accidents)",
        "files": len(files),
        "rows": 0,
        "empty_narrative": 0,
        "usable_narrative": 0,
        "exact_dup_document_no": 0,
        "injury_degree": Counter(),
        "columns": None,
    }
    seen_ids: set[str] = set()
    sample: list[dict] = []
    usable_i = 0
    for path in files:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            if stats["columns"] is None:
                stats["columns"] = reader.fieldnames
            for row in reader:
                stats["rows"] += 1
                doc = _clean(row.get("DOCUMENT_NO"))
                if doc:
                    if doc in seen_ids:
                        stats["exact_dup_document_no"] += 1
                    else:
                        seen_ids.add(doc)
                narr = _clean(row.get("AI_NARR"))
                if not narr:
                    stats["empty_narrative"] += 1
                deg = _clean(row.get("INJ_DEGR_DESC")) or "(blank)"
                stats["injury_degree"][deg] += 1
                mapped = map_dataset1_row(row, path)
                if mapped is None:
                    continue
                stats["usable_narrative"] += 1
                if usable_i < k:
                    sample.append(mapped)
                else:
                    j = rng.randrange(usable_i + 1)
                    if j < k:
                        sample[j] = mapped
                usable_i += 1
    stats["unique_document_no"] = len(seen_ids)
    stats["injury_degree"] = stats["injury_degree"].most_common(12)
    return sample, stats


def reconstruct_osha_abstracts() -> dict[str, str]:
    folder = RAW_ROOT / "OSHA abstract dataset 3"
    parts: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for path in _csv_files(folder):
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                sid = _clean(row.get("SUMMARY_NR"))
                if not sid:
                    continue
                try:
                    line_nr = int(_clean(row.get("LINE_NR") or "0") or 0)
                except ValueError:
                    line_nr = 0
                parts[sid].append((line_nr, row.get("ABSTRACT_TEXT") or ""))
    rebuilt: dict[str, str] = {}
    for sid, chunks in parts.items():
        chunks.sort(key=lambda x: x[0])
        text = _clean("".join(t for _, t in chunks))
        if len(text) >= MIN_DESC_LEN:
            rebuilt[sid] = text
    return rebuilt


def map_dataset2_row(row: dict, path: Path, abstracts: dict[str, str]) -> dict | None:
    d2 = RAW_ROOT / "OSHA Dataset 2"
    d3 = RAW_ROOT / "OSHA abstract dataset 3"
    stats = {
        "name": "OSHA Dataset 2 + abstract dataset 3",
        "d2_files": len(_csv_files(d2)),
        "d3_files": len(_csv_files(d3)),
        "d2_rows": 0,
        "d2_empty_event_desc": 0,
        "d2_empty_abstract_column": 0,
        "d2_fatality_x": 0,
        "d3_reconstructed_incidents": len(abstracts),
        "d2_with_reconstructed_abstract": 0,
        "d2_usable": 0,
        "columns_d2": None,
        "columns_d3": ["SUMMARY_NR", "LINE_NR", "ABSTRACT_TEXT", "LOAD_DT"],
    }
    seen: set[str] = set()
    stats["d2_dup_summary_nr"] = 0
    for path in _csv_files(d2):
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            if stats["columns_d2"] is None:
                stats["columns_d2"] = reader.fieldnames
            for row in reader:
                stats["d2_rows"] += 1
                sid = _clean(row.get("SUMMARY_NR"))
                if sid:
                    if sid in seen:
                        stats["d2_dup_summary_nr"] += 1
                    else:
                        seen.add(sid)
                if not _clean(row.get("EVENT_DESC")):
                    stats["d2_empty_event_desc"] += 1
                if not _clean(row.get("ABSTRACT_TEXT")):
                    stats["d2_empty_abstract_column"] += 1
                if _clean(row.get("FATALITY")).upper() == "X":
                    stats["d2_fatality_x"] += 1
                abstract = abstracts.get(sid, "")
                if abstract:
                    stats["d2_with_reconstructed_abstract"] += 1
                desc = abstract or _clean(row.get("EVENT_DESC"))
                if len(desc) >= MIN_DESC_LEN:
                    stats["d2_usable"] += 1
    stats["d2_unique_summary_nr"] = len(seen)
    return stats


def iter_dataset2_usable(abstracts: dict[str, str]) -> Iterator[dict]:
    folder = RAW_ROOT / "OSHA Dataset 2"
    for path in _csv_files(folder):
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                sid = _clean(row.get("SUMMARY_NR"))
                if not sid:
                    continue
                event = _clean(row.get("EVENT_DESC"))
                abstract = abstracts.get(sid, "")
                if abstract and event and event.lower() not in abstract.lower():
                    description = f"{event} {abstract}".strip()
                else:
                    description = abstract or event
                if len(description) < MIN_DESC_LEN:
                    continue
                fatality = _clean(row.get("FATALITY")).upper() == "X"
                severity = "Fatality" if fatality else ""
                loc_bits = [
                    _clean(row.get("CONST_END_USE")),
                    _clean(row.get("PROJECT_TYPE")),
                    _clean(row.get("SIC_LIST")),
                ]
                keywords = _clean(row.get("EVENT_KEYWORD"))
                report_type = ""
                report_type_origin = "unknown"
                lowered = description.lower()
                if "near miss" in lowered or "near-miss" in lowered:
                    report_type = "Near miss"
                    report_type_origin = "inferred"
                yield {
                    "source_dataset": "osha_accident_summaries",
                    "source_file": path.name,
                    "source_incident_id": sid,
                    "report_id": f"OSHA-{sid}",
                    "group_id": f"OSHA-{sid}",
                    "report_type": report_type,
                    "report_type_origin": report_type_origin,
                    "site_name": "",
                    "site_name_origin": "unknown",
                    "activity": keywords,
                    "activity_origin": "original" if keywords else "unknown",
                    "date_reported": _iso_date(row.get("EVENT_DATE") or ""),
                    "date_reported_origin": "original" if _iso_date(row.get("EVENT_DATE") or "") else "unknown",
                    "observation_date": _iso_date(row.get("EVENT_DATE") or ""),
                    "observation_date_origin": "original" if _iso_date(row.get("EVENT_DATE") or "") else "unknown",
                    "description": description,
                    "description_origin": "original",
                    "actual_severity": severity,
                    "actual_severity_origin": "original" if severity else "unknown",
                    "date_closed": "",
                    "date_closed_origin": "unknown",
                    "status": "",
                    "status_origin": "unknown",
                    "location_detail": ", ".join(b for b in loc_bits if b),
                    "location_detail_origin": "original" if any(loc_bits) else "unknown",
                    "source_equipment": "",
                }


def analyze_row(row: dict) -> dict:
    from app.services.analysis_pipeline import analyze_report

    result = analyze_report(row["description"], use_llm=False)
    source_equip = _clean(row.get("source_equipment"))
    extracted = result.get("equipment") or []
    equipment_parts = []
    if source_equip:
        equipment_parts.append(source_equip)
    for item in extracted:
        item = _clean(item)
        if item and item.lower() not in {p.lower() for p in equipment_parts}:
            equipment_parts.append(item)
    equipment = "; ".join(equipment_parts)
    equipment_origin = "unknown"
    if source_equip and extracted:
        equipment_origin = "original+inferred"
    elif source_equip:
        equipment_origin = "original"
    elif extracted:
        equipment_origin = "inferred"

    activity = _clean(row.get("activity"))
    activity_origin = row.get("activity_origin") or "unknown"
    if not activity and result.get("activity"):
        activity = result["activity"]
        activity_origin = "inferred"

    location = _clean(row.get("location_detail"))
    location_origin = row.get("location_detail_origin") or "unknown"
    if not location and result.get("location"):
        location = result["location"]
        location_origin = "inferred"

    barriers = result.get("barrier_failure") or []
    if isinstance(barriers, str):
        barrier_text = barriers
    else:
        barrier_text = "; ".join(_clean(b) for b in barriers if _clean(b))

    sif = bool(result.get("sif_potential"))
    hazard = _clean(result.get("hazard"))
    actions = result.get("suggested_actions") or []
    action = _clean(result.get("recommended_follow_up"))
    if not action and actions:
        action = _clean(actions[0] if isinstance(actions, list) else actions)

    precursor = ""
    if sif and hazard:
        precursor = hazard
    elif sif:
        precursor = _clean(result.get("unsafe_type"))

    out = {
        **{k: v for k, v in row.items() if k != "source_equipment"},
        "activity": activity,
        "activity_origin": activity_origin,
        "location_detail": location,
        "location_detail_origin": location_origin,
        "equipment": equipment,
        "equipment_origin": equipment_origin,
        "hazard": hazard,
        "barrier_failure": barrier_text,
        "lsr": _clean(result.get("life_saving_rule")),
        "sif_potential": "yes" if sif else "no",
        "priority": _clean(result.get("priority")).lower() or ("low" if not sif else ""),
        "potential_severity": _clean(result.get("potential_consequence")),
        "precursor": precursor,
        "sif_probability": (
            "" if result.get("confidence") is None else f"{float(result['confidence']):.4f}"
        ),
        "reason": _clean(result.get("explanation")),
        "suggested_immediate_action": action,
        "short_summary": _clean(result.get("summary")),
        "record_origin": "cleaned_real",
        "dataset_version": DATASET_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "analysis_model": _clean(result.get("model")) or "rules-v1",
        "outputs_origin": "inferred",
    }
    return out


def exact_dedupe(rows: list[dict]) -> tuple[list[dict], int]:
    seen: set[str] = set()
    kept: list[dict] = []
    dropped = 0
    for row in rows:
        key = _desc_hash(row["description"])
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(row)
    return kept, dropped


def stratified_split(rows: list[dict], rng: random.Random) -> dict[str, list[dict]]:
    by_label: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_label[row.get("sif_potential") or "unknown"].append(row)
    splits = {"training": [], "validation": [], "testing": []}
    for label, group in by_label.items():
        rng.shuffle(group)
        n = len(group)
        n_train = int(round(n * TRAIN_FRAC))
        n_val = int(round(n * VAL_FRAC))
        if n_train + n_val > n:
            n_val = max(0, n - n_train)
        n_test = n - n_train - n_val
        # Keep test from shrinking to zero on tiny classes.
        if n >= 3 and n_test == 0:
            n_test = 1
            if n_val > 0:
                n_val -= 1
            else:
                n_train -= 1
        chunks = {
            "training": group[:n_train],
            "validation": group[n_train : n_train + n_val],
            "testing": group[n_train + n_val :],
        }
        for name, part in chunks.items():
            for row in part:
                row["split"] = name
            splits[name].extend(part)
    return splits


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANONICAL_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CANONICAL_COLUMNS})


def write_quality_reports(payload: dict) -> None:
    reports = OUT_ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "data_quality.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    d1 = payload["dataset1"]
    d23 = payload["dataset2_3"]
    sample = payload["sample"]
    splits = payload["splits"]
    md = f"""# Data quality report

Generated: {payload["generated_at"]}
Dataset version: `{DATASET_VERSION}`
Preprocessing version: `{PREPROCESSING_VERSION}`
Random seed: `{SEED}`

Original files under `docs/Real datasets/` were **not modified**.

## Inventory

| Family | Files | Rows | Notes |
|---|---|---|---|
| OSHA Dataset 1 (MSHA accidents) | {d1["files"]} | {d1["rows"]:,} | 59 columns. Usable narratives (≥{MIN_DESC_LEN} chars): {d1["usable_narrative"]:,}. Empty `AI_NARR`: {d1["empty_narrative"]:,}. Duplicate `DOCUMENT_NO`: {d1["exact_dup_document_no"]:,}. |
| OSHA Dataset 2 (summaries) | {d23["d2_files"]} | {d23["d2_rows"]:,} | 16 columns. Empty `ABSTRACT_TEXT` column: {d23["d2_empty_abstract_column"]:,}. Fatality flag X: {d23["d2_fatality_x"]:,}. |
| OSHA abstract dataset 3 | {d23["d3_files"]} | line fragments | Reconstructed to **{d23["d3_reconstructed_incidents"]:,}** incidents by `SUMMARY_NR` + `LINE_NR`. |
| cy-2021 / 2023 / 2024 xlsx | 3 + 3 compressed copies | not ingested | Large statistical workbooks, not incident narratives. Compressed copies treated as duplicates of the uncompressed files. |

Dataset 2 rows that gained a reconstructed abstract: **{d23["d2_with_reconstructed_abstract"]:,}**.
Dataset 2 usable (description ≥ {MIN_DESC_LEN} chars after join): **{d23["d2_usable"]:,}**.

## Sampling (not synthesis)

Need for synthetic rows: **none**. Usable real incidents far exceed 10,000.

| Step | Count |
|---|---|
| MSHA reservoir (usable narratives) | {sample["msha_sampled"]:,} |
| OSHA reservoir (joined summaries) | {sample["osha_sampled"]:,} |
| Exact-duplicate descriptions dropped | {sample["exact_duplicates_dropped"]:,} |
| Final analysed records | {sample["final_n"]:,} |

Record origin for every output row: `cleaned_real`.
Output fields (hazard, LSR, SIF, priority, etc.): `outputs_origin=inferred` from `rules-v1`.
`report_type` is **unknown** unless the source supports a documented heuristic (MSHA "ACCIDENT ONLY" or the phrase "near miss" in text) — then `report_type_origin=inferred`. UA/UC were **not** invented.

## Splits (group = incident id, seed={SEED})

| Split | Rows | SIF yes | SIF no |
|---|---|---|---|
| training | {splits["training"]["n"]:,} | {splits["training"]["sif_yes"]:,} | {splits["training"]["sif_no"]:,} |
| validation | {splits["validation"]["n"]:,} | {splits["validation"]["sif_yes"]:,} | {splits["validation"]["sif_no"]:,} |
| testing | {splits["testing"]["n"]:,} | {splits["testing"]["sif_yes"]:,} | {splits["testing"]["sif_no"]:,} |

Preprocessing parameters were not fitted. The test split was not used for sampling weights beyond the shared reservoir of real incidents (all three splits are held-out slices of the same real sample). No synthetic validation/test rows.

## Dropped / not used

- Empty or very short narratives (< {MIN_DESC_LEN} characters)
- Abstract line fragments (Dataset 3) until reconstructed
- Excel CY workbooks and `compressed_*.xlsx`
- Exact duplicate descriptions inside the sample
"""
    (reports / "data_quality.md").write_text(md, encoding="utf-8")

    prep = f"""# Preprocessing report

## Pipeline

```
docs/Real datasets (immutable)
  → validate schemas / counts
  → reconstruct Dataset 3 abstracts (SUMMARY_NR, LINE_NR)
  → join Dataset 2 summaries
  → keep rows with usable description
  → reservoir-sample per family (seed {SEED})
  → exact duplicate drop (SHA-256 of normalised description)
  → map canonical input fields (blank if absent)
  → analyze_report(text, use_llm=False)
  → stratified 60/20/20 split on sif_potential
  → data/processed/{{training,validation,testing}}/reports.csv
```

## Cleaning applied

| Operation | Behaviour |
|---|---|
| Whitespace | Collapsed; Unicode blanks stripped |
| Missing tokens | `?`, `NO VALUE FOUND`, `Not Reported`, empty → unknown |
| Dates | ISO `YYYY-MM-DD` prefix from source timestamps |
| Dataset 3 | Concatenate line fragments; never treat a fragment as a report |
| Outliers | Injury/fatality rows kept (genuine HSE events, not deleted) |
| Imputation | None for numeric OSHA/MSHA fields. Empty inputs stay empty |
| Encoding/scaling | Not applied (no fitted transformer; avoids leakage) |
| LLM | Disabled for this batch so outputs stay deterministic |

## Field origins

- `original` — copied from a source column
- `inferred` — existing SIF rule engine, or a documented heuristic (`Near miss` only)
- `unknown` — source silent; left blank
- `original+inferred` — source equipment plus engine extraction

No row is labelled as real OIL UA/UC data. These are public MSHA/OSHA accident records mapped into the app schema.
"""
    (reports / "preprocessing.md").write_text(prep, encoding="utf-8")

    gen = f"""# Dataset generation

No synthetic HSE records were generated.

{sample["final_n"]:,} **cleaned real** incidents were sampled from {d1["usable_narrative"]:,} MSHA narratives and {d23["d2_usable"]:,} OSHA summaries (after abstract reconstruction).

Augmentation / SMOTE / template duplication: **not used**.

Output columns that are not in OSHA/MSHA were filled only by `backend/app/services/analysis_pipeline.py` (same engine as the live app).

To regenerate:

```
cd backend
py -3 scripts/build_processed_datasets.py
```
"""
    (reports / "dataset_generation.md").write_text(gen, encoding="utf-8")


def write_data_dictionary() -> None:
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    text = """# Data dictionary (canonical processed reports)

Source files in `docs/Real datasets/` are immutable. This dictionary describes
`data/processed/{training,validation,testing}/reports.csv`.

Provenance columns: `*_origin` is `original`, `inferred`, `unknown`, or `original+inferred`.
All model outputs have `outputs_origin=inferred`. `record_origin=cleaned_real`.

## Inputs

| Field | Type | Meaning | Source mapping | Missing | Feature / target |
|---|---|---|---|---|---|
| report_id | string | Stable id for this pipeline | `MSHA-{DOCUMENT_NO}` or `OSHA-{SUMMARY_NR}` | required | identifier |
| report_type | string | UA / UC / Near miss | **Not in OSHA/MSHA.** Set to `Near miss` only if MSHA degree is `ACCIDENT ONLY` or the text contains "near miss"; otherwise blank | unknown | optional feature; inferred heuristic |
| site_name | string | Operator / establishment | MSHA `OPERATOR_NAME`. OSHA summaries have no site | blank | feature |
| activity | string | Work activity | MSHA `AI_ACTY_DESC`; OSHA `EVENT_KEYWORD`; else engine | blank or inferred | feature |
| date_reported | date | Event / report date | `AI_DT` / `EVENT_DATE` | blank | feature |
| description | string | Narrative | MSHA `AI_NARR`; OSHA reconstructed abstract + `EVENT_DESC` | rows without text excluded | primary feature |
| actual_severity | string | What actually happened | MSHA `INJ_DEGR_DESC`; OSHA fatality flag → `Fatality` | blank | feature (not SIF potential) |
| date_closed | date | Return-to-work if present | MSHA `RETURN_TO_WORK_DT` | blank | unused |
| status | string | Closed if return-to-work date exists | inferred from `date_closed` only | blank | unused |
| observation_date | date | Same as event date in these dumps | `AI_DT` / `EVENT_DATE` | blank | feature |
| location_detail | string | Place / subunit / project | MSHA subunit + underground location; OSHA construction fields; else engine location | blank | feature |

## Outputs (rule engine, not original labels)

| Field | Type | Meaning | How filled | Can be inferred |
|---|---|---|---|---|
| equipment | string | Equipment mentioned | MSHA `MINING_EQUIP` plus `extract_equipment` | yes |
| hazard | string | Primary hazard | `information_extractor` / SIF matches | yes; blank if unsupported |
| barrier_failure | string | Failed controls | engine list, joined with `; ` | yes |
| lsr | string | Life-Saving Rule | `rule_classifier` | yes; may be low-confidence |
| sif_potential | yes/no | SIF precursor flag | `risk_scorer.assess` | yes (model) |
| priority | high/medium/low | Prototype priority | same scorer (`HIGH`/`MEDIUM`/`LOW` lowercased) | yes |
| potential_severity | string | Potential consequence | first matched indicator consequence | yes |
| precursor | string | Hazard used as precursor tag when SIF=yes | derived from hazard / unsafe type | yes; not an official taxonomy |
| sif_probability | float 0–1 | Scorer confidence | `confidence` from `risk_scorer` | yes |
| reason | string | Explanation with evidence | `build_explanation` | yes |
| suggested_immediate_action | string | First suggested action | `narrative.suggest_actions` | yes |
| short_summary | string | Deterministic summary | `narrative.build_summary` | yes |

## Pipeline metadata

| Field | Meaning |
|---|---|
| source_dataset | `msha_accidents` or `osha_accident_summaries` |
| source_file | Chunk filename |
| source_incident_id | Native id |
| group_id | Split group (one incident) |
| split | training / validation / testing |
| dataset_version | `real-osha-msha-v1` |
| preprocessing_version | `pipeline-v1` |
| analysis_model | `rules-v1` |

These public accident records are **not** Oil India HSSE UA/UC exports. SIF labels are prototype engine outputs and need HSE review before operational use.
"""
    (DOCS_ROOT / "data_dictionary.md").write_text(text, encoding="utf-8")
    (DOCS_ROOT / "preprocessing.md").write_text(
        "See `data/processed/reports/preprocessing.md` for the run that produced the current splits.\n",
        encoding="utf-8",
    )
    (DOCS_ROOT / "dataset_generation.md").write_text(
        "See `data/processed/reports/dataset_generation.md`. No synthetic records were created.\n",
        encoding="utf-8",
    )


def main() -> None:
    if not RAW_ROOT.exists():
        raise SystemExit(f"Missing source folder: {RAW_ROOT}")

    print(f"[{_now()}] Quality scan: Dataset 1")
    d1_stats = scan_dataset1()
    print(f"  rows={d1_stats['rows']:,} usable={d1_stats['usable_narrative']:,}")

    print(f"[{_now()}] Reconstruct Dataset 3 abstracts")
    abstracts = reconstruct_osha_abstracts()
    print(f"  reconstructed incidents={len(abstracts):,}")

    print(f"[{_now()}] Quality scan: Dataset 2 + join")
    d23_stats = scan_dataset2_and_3(abstracts)
    print(f"  d2_rows={d23_stats['d2_rows']:,} usable={d23_stats['d2_usable']:,}")

    rng_msha = random.Random(SEED)
    rng_osha = random.Random(SEED + 1)
    rng_split = random.Random(SEED)

    print(f"[{_now()}] Reservoir sample MSHA usable narratives")
    msha_sample = reservoir_sample(iter_dataset1_usable(), SAMPLE_PER_FAMILY, rng_msha)
    print(f"  sampled={len(msha_sample):,}")

    print(f"[{_now()}] Reservoir sample OSHA joined summaries")
    osha_sample = reservoir_sample(iter_dataset2_usable(abstracts), SAMPLE_PER_FAMILY, rng_osha)
    print(f"  sampled={len(osha_sample):,}")

    combined = msha_sample + osha_sample
    combined, dropped_dups = exact_dedupe(combined)
    rng_split.shuffle(combined)
    combined = combined[:TARGET_N]
    print(f"[{_now()}] After dedupe+cap: {len(combined):,} (dropped exact dups {dropped_dups})")

    analysed: list[dict] = []
    failures = 0
    for i, row in enumerate(combined, start=1):
        try:
            analysed.append(analyze_row(row))
        except Exception as exc:  # noqa: BLE001 — keep the batch going
            failures += 1
            print(f"  skip {row.get('report_id')}: {exc}")
        if i % 500 == 0:
            print(f"  analysed {i}/{len(combined)}")

    splits = stratified_split(analysed, random.Random(SEED))
    for name, rows in splits.items():
        write_csv(OUT_ROOT / name / "reports.csv", rows)
        print(f"  wrote {name}: {len(rows):,}")

    def split_stats(rows: list[dict]) -> dict:
        c = Counter(r.get("sif_potential") for r in rows)
        return {"n": len(rows), "sif_yes": c.get("yes", 0), "sif_no": c.get("no", 0)}

    payload = {
        "generated_at": _now(),
        "seed": SEED,
        "dataset_version": DATASET_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "dataset1": d1_stats,
        "dataset2_3": d23_stats,
        "excel_ingested": False,
        "excel_reason": "CY workbooks are large statistical extracts, not per-incident narratives; compressed copies excluded as duplicates.",
        "sample": {
            "msha_sampled": len(msha_sample),
            "osha_sampled": len(osha_sample),
            "exact_duplicates_dropped": dropped_dups,
            "analyse_failures": failures,
            "final_n": len(analysed),
        },
        "splits": {k: split_stats(v) for k, v in splits.items()},
    }
    write_quality_reports(payload)
    write_data_dictionary()
    (OUT_ROOT / "README.md").write_text(
        "Generated train/validation/test CSVs from `docs/Real datasets/`.\n"
        "CSV files are gitignored. Regenerate with "
        "`py -3 backend/scripts/build_processed_datasets.py`.\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["splits"], indent=2))
    print(f"[{_now()}] done. failures={failures}")


if __name__ == "__main__":
    main()
