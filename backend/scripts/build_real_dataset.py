"""Build a REAL-DATA SIF training/validation/test set from the raw source files.

Sources (all read-only; nothing under ``docs/Real datasets/`` is ever written):

  1. OSHA Dataset 1      — MSHA mine accidents (59 columns, chunked CSVs).
                            Description = ``AI_NARR`` (many are empty).
  2. OSHA Dataset 2      — OSHA incident summaries. ``ABSTRACT_TEXT`` is usually
                            empty, but ``EVENT_DESC`` is populated for every row
                            (short real incident headline) and ``FATALITY`` = 'X'
                            flags fatalities.
  3. OSHA abstract set 3 — line-split fatality narratives. Reconstructed by
                            grouping ``SUMMARY_NR`` and sorting ``LINE_NR``
                            BEFORE a row is treated as a report.
  4. BSEE xlsx (cy-2021 / cy-2023 / cy-2024) — offshore incident statistics.
                            ``compressed_*`` files duplicate the uncompressed
                            ones (identical shared strings; sheet XML differs by
                            ~1 KB of metadata) and are skipped.

Pipeline phases (``--phase``):

  extract : read every source, map onto the canonical INPUT schema, write
            ``data/processed/_cache/extracted_*.csv`` and the FIRST DELIVERABLE
            reports: column mapping + data-quality report (with reconstructed
            abstract counts).  No analysis, no splits.
  analyze : sample ~12,000 candidates (seeded), run every description through
            the existing backend engine (``analysis_pipeline.analyze_report``,
            ``use_llm=False`` — deterministic, no API), map the engine result
            onto the canonical OUTPUT schema, cache the analyzed rows.
  split   : clean (length filter + exact-fingerprint dedupe), then a
            deterministic 60/20/20 split grouped by ``incident_id`` and
            stratified on ``sif_potential`` (seed 42, done BEFORE any scaler/
            encoder fit). Writes the three split CSVs + data dictionary.
  all     : extract -> analyze -> split.

Rules honoured here:

  * Originals are never touched; only ``data/processed/`` is written.
  * A canonical INPUT field is left empty when the source does not provide it.
    ``model_inferred_value`` provenance is recorded per row: OUTPUT fields are
    always pipeline-derived from the description (never template-randomized),
    and an INPUT field that is *derived* by a documented heuristic (e.g. BSEE
    ``actual_severity`` from injury/fatality counts) is flagged ``inferred``.
  * ``report_type`` is the actual source label (MSHA mine accident / OSHA
    incident summary / OSHA fatality narrative / BSEE offshore incident) — the
    UA/UC/Near-miss taxonomy is NOT in these datasets, so it is never
    fabricated.
  * Split is grouped by incident id (fragments of one event never cross
    splits) and stratified on ``sif_potential``.
  * No model training, no scaler/encoder fitting, no test-set touching here.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.analysis_pipeline import analyze_report  # noqa: E402
from app.services.ingest import _text_fingerprint, parse_date  # noqa: E402

DATA_DIR = ROOT / "data" / "processed"
CACHE_DIR = DATA_DIR / "_cache"
REPORTS_DIR = DATA_DIR / "reports"

RAW = ROOT / "docs" / "Real datasets"

SEED = 42
TARGET = 10_000
MIN_DESC_LEN = 15          # descriptions shorter than this are dropped (documented)
CANDIDATE_CAP = 12_500     # sampled candidates before dedupe/cleaning

# Source-priority used when the same incident text appears in several sources
# (keeps the richest description).  Lower number = kept first.
_SOURCE_PRIORITY = {"osha_abstract": 0, "msha": 1, "bsee": 2, "osha_summary": 3}

CANONICAL_INPUTS = [
    "report_id", "incident_id", "report_type", "site_name", "activity",
    "date_reported", "description", "actual_severity", "date_closed",
    "status", "observation_date", "location_detail",
]

CANONICAL_OUTPUTS = [
    "equipment", "hazard", "barrier_failure", "lsr", "sif_potential",
    "priority", "potential_severity", "precursor", "sif_probability",
    "reason", "suggested_immediate_action", "short_summary",
]

PROVENANCE_COLS = [
    "source_name", "source_file", "inferred_fields", "model_tag",
    "languages", "description_len",
]

FINAL_COLUMNS = CANONICAL_INPUTS + CANONICAL_OUTPUTS + PROVENANCE_COLS


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:10_000]


def _cell(value, default: str = "") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s and s.lower() not in {"nan", "none", "na", "n/a", "-", "--", "null"} else default


def _chunk_paths(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.csv"))


# ---------------------------------------------------------------------------
# extraction: source -> canonical rows
# ---------------------------------------------------------------------------

def extract_msha() -> list[dict]:
    """OSHA Dataset 1 — MSHA mine accidents. AI_NARR is the description."""
    rows: list[dict] = []
    for path in _chunk_paths(RAW / "OSHA Dataset 1"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for i, r in enumerate(csv.DictReader(f), start=1):
                desc = _clean_text(r.get("AI_NARR"))
                mine_id = _cell(r.get("MINE_ID"))
                ai_dt = _cell(r.get("AI_DT"))
                doc_no = _cell(r.get("DOCUMENT_NO")) or "nd"
                incident_id = f"{mine_id}|{ai_dt}|{doc_no}"
                rows.append({
                    "report_id": f"MSHA-{mine_id}-{ai_dt}-{doc_no}-{i:06d}",
                    "incident_id": incident_id,
                    "report_type": "MSHA mine accident",
                    "site_name": _cell(r.get("OPERATOR_NAME")) or _cell(r.get("CONTROLLER_NAME")),
                    "activity": _cell(r.get("AI_ACTY_DESC"))[:128],
                    "date_reported": (parse_date(ai_dt).isoformat() if parse_date(ai_dt) else ""),
                    "description": desc,
                    "actual_severity": _cell(r.get("INJ_DEGR_DESC"))[:64],
                    "date_closed": "",
                    "status": "",
                    "observation_date": "",
                    "location_detail": _cell(r.get("UG_LOCATION"))[:128],
                    "source_name": "msha",
                    "source_file": path.name,
                    # structured richness kept for the cache / quality report
                    "_accident_type": _cell(r.get("ACCIDENT_TYPE")),
                    "_injury_source": _cell(r.get("INJURY_SOURCE")),
                    "_nature_injury": _cell(r.get("NATURE_INJURY")),
                    "_equipment": _cell(r.get("MINING_EQUIP")),
                    "_days_lost": _cell(r.get("DAYS_LOST")),
                    "_state": _cell(r.get("FIPS_STATE_CD")),
                })
    return rows


def extract_osha_summary() -> list[dict]:
    """OSHA Dataset 2 — summaries. EVENT_DESC (100% populated) is the text."""
    rows: list[dict] = []
    for path in _chunk_paths(RAW / "OSHA Dataset 2"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                summary_nr = _cell(r.get("SUMMARY_NR"))
                fatality = _cell(r.get("FATALITY"))
                rows.append({
                    "report_id": f"OSHA-SUM-{summary_nr}",
                    "incident_id": f"OSHA-SUM-{summary_nr}",
                    "report_type": "OSHA incident summary",
                    "site_name": "",
                    "activity": "",
                    "date_reported": (parse_date(_cell(r.get("EVENT_DATE"))).isoformat()
                                      if parse_date(_cell(r.get("EVENT_DATE"))) else ""),
                    "description": _clean_text(r.get("EVENT_DESC")),
                    "actual_severity": "Fatality" if fatality.upper() == "X" else "",
                    "date_closed": "",
                    "status": "",
                    "observation_date": "",
                    "location_detail": "",
                    "source_name": "osha_summary",
                    "source_file": path.name,
                    "_keyword": _cell(r.get("EVENT_KEYWORD")),
                    "_project_type": _cell(r.get("PROJECT_TYPE")),
                    "_sic": _cell(r.get("SIC_LIST")),
                    "_state_flag": _cell(r.get("STATE_FLAG")),
                    "_fatality": fatality,
                })
    return rows


def extract_osha_abstract() -> tuple[list[dict], dict]:
    """OSHA abstract set 3 — line-split abstracts, reconstructed by
    (SUMMARY_NR, LINE_NR).  Returns (rows, reconstruction_counts)."""
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    counts = {"line_rows": 0, "unique_summary_nr": 0, "multi_line": 0,
              "single_line": 0, "zero_text": 0, "max_lines": 0}
    for path in _chunk_paths(RAW / "OSHA abstract dataset 3"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                counts["line_rows"] += 1
                nr = _cell(r.get("SUMMARY_NR"))
                if not nr:
                    continue
                line_nr = 0
                try:
                    line_nr = int(r.get("LINE_NR") or 0)
                except ValueError:
                    pass
                groups[nr].append((line_nr, r.get("ABSTRACT_TEXT") or ""))
    counts["unique_summary_nr"] = len(groups)
    for nr, lines in groups.items():
        if len(lines) > 1:
            counts["multi_line"] += 1
        else:
            counts["single_line"] += 1
        counts["max_lines"] = max(counts["max_lines"], len(lines))
        if not any(t.strip() for _, t in lines):
            counts["zero_text"] += 1

    rows: list[dict] = []
    for nr, lines in groups.items():
        ordered = sorted(lines, key=lambda x: x[0])
        desc = _clean_text(" ".join(t for _, t in ordered))
        rows.append({
            "report_id": f"OSHA-ABS-{nr}",
            "incident_id": f"OSHA-ABS-{nr}",
            "report_type": "OSHA fatality narrative",
            "site_name": "",
            "activity": "",
            "date_reported": "",
            "description": desc,
            "actual_severity": "Fatality",
            "date_closed": "",
            "status": "",
            "observation_date": "",
            "location_detail": "",
            "source_name": "osha_abstract",
            "source_file": "OSHA abstract dataset 3 (reconstructed)",
            "_line_count": len(lines),
        })
    return rows, counts


def extract_bsee() -> tuple[list[dict], dict]:
    """BSEE offshore incident xlsx (2021/2023/2024). compressed_* skipped:
    they duplicate the uncompressed sheets (identical sharedStrings)."""
    rows: list[dict] = []
    notes: dict = {}
    for year in ("2021", "2023", "2024"):
        path = RAW / f"cy-{year}-excel-spreadsheet.xlsx"
        if not path.exists():
            notes[year] = "missing"
            continue
        try:
            import pandas as pd
        except ImportError:
            raise SystemExit("pandas is required for the BSEE xlsx extraction")
        sheet = f"CY{year} Incidents"
        usecols = ["SN_EV_MASTERS", "Date", "Operator Name", "Incident Summary",
                   "Structure Name", "Area Name", "Block",
                   "Operator Fatalities", "Contractor Fatalities",
                   "Operator Number Injuries >3 Days LT ",
                   "Contractor Number Injuries >3 Days LT ",
                   "Operator Number Injuries 1-3 Days LT",
                   "Contractor Number Injuries 1-3 Days LT",
                   "Operator Number Injuries >3 Days RW",
                   "Contractor Number Injuries >3 Days RW",
                   "Operator Number Injuries 1-3 Days RW",
                   "Contractor Number Injuries 1-3 Days RW",
                   "Contractor Number of Other Injuries",
                   "Operator Number of Other Injuries",
                   "Production", "Drilling", "Workover", "Completion",
                   "Motor Vessel", "Pipeline", "Helicopter", "Other Operation",
                   "Exploration", "Development Production",
                   "Equipment Failure", "Human Error", "Slip Trip and Fall",
                   "Weather", "External Damage", "Leak"]
        df = pd.read_excel(path, sheet_name=sheet, header=1, usecols=lambda c: c in usecols)
        notes[year] = f"{len(df)} rows"
        for _, r in df.iterrows():
            sn = _cell(r.get("SN_EV_MASTERS"))
            if not sn:
                continue
            fatalities = 0
            injuries = 0
            for col in ("Operator Fatalities", "Contractor Fatalities"):
                try:
                    fatalities += int(float(r.get(col) or 0))
                except (TypeError, ValueError):
                    pass
            for col in df.columns:
                if "Injuries" in col:
                    try:
                        injuries += int(float(r.get(col) or 0))
                    except (TypeError, ValueError):
                        pass
            if fatalities > 0:
                severity = "Fatality"
            elif injuries > 0:
                severity = "Injury"
            else:
                severity = ""
            ops = [c for c in ("Production", "Drilling", "Workover", "Completion",
                               "Motor Vessel", "Pipeline", "Helicopter",
                               "Exploration", "Development Production")
                   if str(r.get(c) or "").strip().upper() == "Y"]
            other_op = _cell(r.get("Other Operation"))
            if other_op:
                ops.append(other_op)
            loc = _cell(r.get("Structure Name")) or (
                f"{_cell(r.get('Area Name'))} {_cell(r.get('Block'))}".strip())
            rows.append({
                "report_id": f"BSEE-{year}-{sn}",
                "incident_id": f"BSEE-{year}-{sn}",
                "report_type": "BSEE offshore incident",
                "site_name": _cell(r.get("Operator Name"))[:128],
                "activity": " / ".join(ops)[:128],
                "date_reported": (parse_date(_cell(r.get("Date"))).isoformat()
                                  if parse_date(_cell(r.get("Date"))) else ""),
                "description": _clean_text(r.get("Incident Summary")),
                "actual_severity": severity,  # derived from counts -> flagged inferred
                "date_closed": "",
                "status": "",
                "observation_date": "",
                "location_detail": loc[:128],
                "source_name": "bsee",
                "source_file": path.name,
                "_fatalities": fatalities,
                "_injuries": injuries,
                "_causes": " / ".join(c for c in ("Equipment Failure", "Human Error",
                                                  "Slip Trip and Fall", "Weather",
                                                  "External Damage", "Leak")
                                      if str(r.get(c) or "").strip().upper() == "Y"),
            })
    return rows, notes


def extract_all() -> dict[str, list[dict]]:
    print("extracting MSHA ...")
    msha = extract_msha()
    print("extracting OSHA summaries ...")
    osha_sum = extract_osha_summary()
    print("extracting OSHA abstracts (reconstructing) ...")
    osha_abs, abs_counts = extract_osha_abstract()
    print("extracting BSEE xlsx (one-time, slow) ...")
    bsee, bsee_notes = extract_bsee()
    return {"msha": msha, "osha_summary": osha_sum, "osha_abstract": osha_abs,
            "bsee": bsee}, abs_counts, bsee_notes


def _write_cache(name: str, rows: list[dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / name
    keys = list(rows[0].keys()) if rows else []
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  cached {len(rows)} rows -> {path.relative_to(ROOT)}")


def _load_cache(name: str) -> list[dict]:
    path = CACHE_DIR / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# deliverable 1: column mapping + data quality report
# ---------------------------------------------------------------------------

def _canonical_mapping_doc() -> str:
    mapping: dict[str, list[tuple[str, str, str]]] = {
        # source: (canonical field, source column, note)
        "msha (OSHA Dataset 1)": [
            ("report_id", "MINE_ID + AI_DT + DOCUMENT_NO + seq", "composite key"),
            ("incident_id", "MINE_ID | AI_DT | DOCUMENT_NO", "one row per accident normally; groups multi-injury rows of one event"),
            ("report_type", "(constant)", "MSHA mine accident — source is the MSHA accident/injury table"),
            ("site_name", "OPERATOR_NAME (fallback CONTROLLER_NAME)", "original"),
            ("activity", "AI_ACTY_DESC", "original"),
            ("date_reported", "AI_DT", "accident date, original"),
            ("description", "AI_NARR", "accident narrative; empty values dropped"),
            ("actual_severity", "INJ_DEGR_DESC", "original (e.g. Fatal / Nonfatal)"),
            ("date_closed", "(none)", "left empty — not present in source"),
            ("status", "(none)", "left empty"),
            ("observation_date", "(none)", "left empty"),
            ("location_detail", "UG_LOCATION (+ FIPS_STATE_CD in cache)", "original"),
        ],
        "osha_summary (OSHA Dataset 2)": [
            ("report_id", "SUMMARY_NR", "original"),
            ("incident_id", "SUMMARY_NR", "original"),
            ("report_type", "(constant)", "OSHA incident summary"),
            ("site_name", "(none)", "left empty"),
            ("activity", "(none)", "left empty"),
            ("date_reported", "EVENT_DATE", "original"),
            ("description", "EVENT_DESC", "headline text; ABSTRACT_TEXT is empty for these rows"),
            ("actual_severity", "FATALITY", "'X' mapped to Fatality, else empty"),
            ("date_closed", "(none)", "left empty"),
            ("status", "(none)", "left empty"),
            ("observation_date", "(none)", "left empty"),
            ("location_detail", "(none)", "left empty (STATE_FLAG/SIC_LIST kept in cache)"),
        ],
        "osha_abstract (OSHA abstract set 3)": [
            ("report_id", "SUMMARY_NR", "original"),
            ("incident_id", "SUMMARY_NR", "original"),
            ("report_type", "(constant)", "OSHA fatality narrative"),
            ("site_name", "(none)", "left empty (extractable from text by the pipeline)"),
            ("activity", "(none)", "left empty"),
            ("date_reported", "(none)", "left empty (the narrative mentions dates in free text)"),
            ("description", "ABSTRACT_TEXT grouped by SUMMARY_NR, sorted by LINE_NR", "RECONSTRUCTED before the row is treated as a report"),
            ("actual_severity", "(constant)", "Fatality — this file is the OSHA fatality narrative set"),
            ("date_closed", "(none)", "left empty"),
            ("status", "(none)", "left empty"),
            ("observation_date", "(none)", "left empty"),
            ("location_detail", "(none)", "left empty"),
        ],
        "bsee (cy-2021/2023/2024 xlsx)": [
            ("report_id", "SN_EV_MASTERS", "original"),
            ("incident_id", "SN_EV_MASTERS", "original"),
            ("report_type", "(constant)", "BSEE offshore incident"),
            ("site_name", "Operator Name", "original"),
            ("activity", "operation flag columns (Production/Drilling/...)", "DERIVED — Y-flagged operation mapped to label, flagged inferred"),
            ("date_reported", "Date", "original"),
            ("description", "Incident Summary", "original free text"),
            ("actual_severity", "Operator/Contractor Fatalities + injury count columns", "DERIVED — Fatality if any fatality count > 0, else Injury if any injury count > 0, else empty; flagged inferred"),
            ("date_closed", "(none)", "left empty"),
            ("status", "(none)", "left empty"),
            ("observation_date", "(none)", "left empty"),
            ("location_detail", "Structure Name (fallback Area Name + Block)", "original"),
        ],
    }
    lines = [
        "# Column mapping — real source files to canonical schema",
        "",
        "Every canonical field below is either **original** (read directly from a source",
        "column), **derived** (computed from source columns by a documented heuristic and",
        "flagged `inferred` in the row provenance), or **empty** (the source does not",
        "provide it — it is never fabricated).",
        "",
        "## Canonical schema",
        "",
        "**Inputs (11):** " + ", ".join(CANONICAL_INPUTS),
        "",
        "**Outputs (12, computed by the existing engine from the description):** "
        + ", ".join(CANONICAL_OUTPUTS),
        "",
        "**Provenance:** " + ", ".join(PROVENANCE_COLS),
        "",
    ]
    for source, pairs in mapping.items():
        lines.append(f"## {source}")
        lines.append("")
        lines.append("| canonical field | source column(s) | handling |")
        lines.append("|---|---|---|")
        for field, col, note in pairs:
            lines.append(f"| {field} | `{col}` | {note} |")
        lines.append("")
    lines.append("## report_type honesty note")
    lines.append("")
    lines.append("The UA / UC / Near-miss taxonomy is NOT present in any of these four")
    lines.append("sources, so `report_type` carries the true source label instead"
                 " (MSHA mine accident / OSHA incident summary / OSHA fatality"
                 " narrative / BSEE offshore incident). No near-miss classification is")
    lines.append("fabricated.")
    lines.append("")
    lines.append("## Compressed xlsx files")
    lines.append("")
    lines.append("`compressed_cy-*-excel-spreadsheet.xlsx` duplicate the uncompressed")
    lines.append("sheets (identical sharedStrings; sheet XML differs by ~1 KB of")
    lines.append("metadata). They are skipped.")
    return "\n".join(lines)


def _write_quality_report(extracted: dict[str, list[dict]], abs_counts: dict,
                          bsee_notes: dict) -> dict:
    lines = [
        "# Data quality report — real source files",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} by "
        "`backend/scripts/build_real_dataset.py`.",
        "",
        "## Raw row counts",
        "",
        "| source | raw rows | rows with non-empty description |",
        "|---|---|---|",
    ]
    summary: dict[str, dict] = {}
    for name, rows in extracted.items():
        nonempty = sum(1 for r in rows if r["description"].strip())
        lines.append(f"| {name} | {len(rows)} | {nonempty} |")
        summary[name] = {"raw": len(rows), "nonempty": nonempty}
    lines += [
        "",
        "## OSHA abstract set 3 — reconstruction counts",
        "",
        f"- line rows in source: **{abs_counts['line_rows']}**",
        f"- unique SUMMARY_NR (reconstructed reports): **{abs_counts['unique_summary_nr']}**",
        f"- multi-line narratives: **{abs_counts['multi_line']}**",
        f"- single-line narratives: **{abs_counts['single_line']}**",
        f"- narratives with zero text after reconstruction: **{abs_counts['zero_text']}**",
        f"- longest narrative (lines): **{abs_counts['max_lines']}**",
        "",
        "## BSEE xlsx rows",
        "",
    ]
    for year, note in bsee_notes.items():
        lines.append(f"- cy-{year}: {note}")
    lines.append("")
    lines.append("## Description length distribution (non-empty descriptions)")
    lines.append("")
    lines.append("| source | n | median chars | mean chars | p90 chars | max chars |")
    lines.append("|---|---|---|---|---|---|")
    for name, rows in extracted.items():
        lens = sorted(len(r["description"]) for r in rows if r["description"].strip())
        if not lens:
            continue
        median = lens[len(lens) // 2]
        mean = sum(lens) / len(lens)
        p90 = lens[int(len(lens) * 0.9)] if lens else 0
        lines.append(f"| {name} | {len(lens)} | {median} | {mean:.0f} | {p90} | {lens[-1]} |")
    lines.append("")
    lines.append("## Missingness of canonical INPUT fields (non-empty description rows)")
    lines.append("")
    lines.append("| source | report_id | site | activity | date | actual_severity | location |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, rows in extracted.items():
        valid = [r for r in rows if r["description"].strip()]
        if not valid:
            continue
        def miss(field: str) -> int:
            return sum(1 for r in valid if not r[field].strip())
        lines.append(
            f"| {name} | {miss('report_id')} | {miss('site_name')} | {miss('activity')} "
            f"| {miss('date_reported')} | {miss('actual_severity')} | {miss('location_detail')} |"
        )
    lines.append("")
    lines.append("## Extraction notes")
    lines.append("")
    lines.append("- OSHA Dataset 2: `ABSTRACT_TEXT` is empty on every row; `EVENT_DESC` is "
                 "populated for all of them and is used as the description.")
    lines.append("- OSHA Dataset 1: `AI_NARR` is empty for a large share of rows; those rows "
                 "are counted above and excluded from candidates.")
    lines.append("- BSEE `actual_severity` is derived from fatality/injury counts and is "
                 "flagged `inferred` in row provenance.")
    lines.append("")
    return "\n".join(lines), summary


# ---------------------------------------------------------------------------
# analyze phase
# ---------------------------------------------------------------------------

_OUTPUT_MAP = {
    "equipment": lambda r: "; ".join(r.get("equipment") or []),
    "hazard": lambda r: r.get("hazard") or "",
    "barrier_failure": lambda r: "; ".join(r.get("barrier_failure") or []),
    "lsr": lambda r: r.get("life_saving_rule") or "",
    "sif_potential": lambda r: "1" if r.get("sif_potential") else "0",
    "priority": lambda r: r.get("priority") or "",
    "potential_severity": lambda r: r.get("potential_consequence") or "",
    "precursor": lambda r: "; ".join(r.get("evidence") or []),
    "sif_probability": lambda r: str(r.get("confidence") or ""),
    "reason": lambda r: r.get("explanation") or "",
    "suggested_immediate_action": lambda r: "; ".join(r.get("suggested_actions") or []),
    "short_summary": lambda r: (r.get("summary") or "")[:500],
}


def _analyze_one(row: dict) -> dict | None:
    desc = row.get("description", "").strip()
    if not desc:
        return None
    try:
        res = analyze_report(desc, use_llm=False)
    except Exception:  # row-level isolation — never kill the batch
        return None
    out = dict(row)
    for field, fn in _OUTPUT_MAP.items():
        out[field] = fn(res)
    out["model_tag"] = res.get("model") or "rules-v1"
    out["languages"] = "; ".join(res.get("languages") or [])
    # provenance: which fields were NOT original source values
    derived_inputs = []
    if row.get("source_name") == "bsee":
        if row.get("actual_severity"):
            derived_inputs.append("actual_severity")
        if row.get("activity"):
            derived_inputs.append("activity")
    out["inferred_fields"] = ",".join(
        ["equipment", "hazard", "barrier_failure", "lsr", "potential_severity",
         "precursor", "sif_probability", "reason", "suggested_immediate_action",
         "short_summary"] + derived_inputs
    )
    out["description_len"] = len(desc)
    return out


def run_analyze(extracted: dict[str, list[dict]], target: int = TARGET) -> list[dict]:
    rng = random.Random(SEED)

    # 1) candidate sampling: BSEE all, others sampled with per-source caps that
    #    land near `target` after dedupe.
    caps = {"bsee": 10 ** 9}
    remainder = target
    for name in ("osha_abstract", "msha", "osha_summary"):
        nonempty = sum(1 for r in extracted[name] if r["description"].strip())
        caps[name] = max(1, int(remainder * 0.45))
        remainder -= caps[name]

    candidates: list[dict] = []
    for name, rows in extracted.items():
        valid = [r for r in rows if r["description"].strip()]
        cap = min(caps.get(name, 10 ** 9), len(valid))
        sample = rng.sample(valid, cap)
        print(f"  {name}: {len(valid)} valid -> sampled {cap}")
        candidates.extend(sample)

    print(f"analyzing {len(candidates)} candidates with the engine ...")
    started = time.time()
    analyzed: list[dict] = []
    errors = 0
    for i, row in enumerate(candidates, start=1):
        out = _analyze_one(row)
        if out is None:
            errors += 1
        else:
            analyzed.append(out)
        if i % 2000 == 0:
            print(f"  {i}/{len(candidates)} ({time.time() - started:.0f}s, "
                  f"{i / max(time.time() - started, 0.01):.0f}/s)")
    _write_cache("analyzed.csv", analyzed)
    print(f"analyzed {len(analyzed)} rows, {errors} engine failures in "
          f"{time.time() - started:.0f}s")
    return analyzed


# ---------------------------------------------------------------------------
# split phase
# ---------------------------------------------------------------------------

def _split_buckets(incidents: list[dict]) -> dict[str, str]:
    """Deterministic 60/20/20 split: within each stratum (sif_potential value)
    incident ids are sorted and dealt round-robin across 10 buckets; buckets
    0-5 -> train, 6-7 -> validation, 8-9 -> test."""
    strata: dict[str, list[str]] = defaultdict(list)
    for inc in incidents:
        strata[inc["stratum"]].append(inc["incident_id"])
    bucket: dict[str, int] = {}
    for stratum, ids in strata.items():
        for offset, iid in enumerate(sorted(ids)):
            bucket[iid] = offset % 10
    split_of = {"train": {0, 1, 2, 3, 4, 5},
                "validation": {6, 7},
                "test": {8, 9}}
    mapping: dict[str, str] = {}
    for iid, b in bucket.items():
        for name, buckets in split_of.items():
            if b in buckets:
                mapping[iid] = name
                break
    return mapping


def run_split(analyzed: list[dict]) -> dict:
    # --- cleaning ---------------------------------------------------------
    total = len(analyzed)
    for row in analyzed:
        try:
            row["description_len"] = int(row.get("description_len") or 0)
        except (TypeError, ValueError):
            row["description_len"] = 0
    too_short = [r for r in analyzed if r["description_len"] < MIN_DESC_LEN]
    kept = [r for r in analyzed if r["description_len"] >= MIN_DESC_LEN]

    # exact-fingerprint dedupe, source-priority keeps the richest description
    seen: dict[str, str] = {}
    deduped: list[dict] = []
    dupe_drops = 0
    for row in sorted(kept, key=lambda r: _SOURCE_PRIORITY.get(r["source_name"], 9)):
        fp = _text_fingerprint(row["description"])
        if fp in seen:
            dupe_drops += 1
            continue
        seen[fp] = row["report_id"]
        deduped.append(row)

    # --- deterministic grouped + stratified split ------------------------
    incidents: dict[str, dict] = {}
    for row in deduped:
        inc = incidents.setdefault(
            row["incident_id"],
            {"incident_id": row["incident_id"], "stratum": "", "rows": []},
        )
        inc["stratum"] = row["sif_potential"]  # stratify on the label
        inc["rows"].append(row)
    mapping = _split_buckets(list(incidents.values()))

    splits = {"train": [], "validation": [], "test": []}
    for iid, inc in incidents.items():
        splits[mapping[iid]].extend(inc["rows"])

    # write final CSVs
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        rows = sorted(rows, key=lambda r: r["report_id"])
        path = DATA_DIR / f"{name}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FINAL_COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"  wrote {name}.csv: {len(rows)} rows")

    return {
        "total_analyzed": total,
        "too_short": len(too_short),
        "dupe_drops": dupe_drops,
        "final": {k: len(v) for k, v in splits.items()},
        "sif_by_split": {
            k: {"sif": sum(1 for r in v if r["sif_potential"] == "1"), "n": len(v)}
            for k, v in splits.items()
        },
    }


# ---------------------------------------------------------------------------
# data dictionary
# ---------------------------------------------------------------------------

def _write_data_dictionary() -> None:
    lines = [
        "# Data dictionary — canonical fields",
        "",
        "Every row in `data/processed/{train,validation,test}.csv` has the same"
        " canonical schema. Values are either **original** (read from a source"
        " column), **empty** (the source did not provide the field — never"
        " fabricated), or **inferred** (derived by the documented engine / a"
        " documented heuristic). The `inferred_fields` column lists, per row,"
        " every canonical field whose value is model-derived or heuristic-derived.",
        "",
        "## Input fields",
        "",
        "| field | type | missingness handling | original vs inferred |",
        "|---|---|---|---|",
        "| report_id | str | composite from source keys (see column mapping) | original |",
        "| incident_id | str | grouping key; fragments of one event never cross splits | original |",
        "| report_type | str | constant per source — never UA/UC/Near-miss (not in these datasets) | original |",
        "| site_name | str | empty when source lacks it (OSHA sets) | original |",
        "| activity | str | empty when source lacks it; BSEE value mapped from Y-flagged operation columns | original / inferred (BSEE) |",
        "| date_reported | str (ISO) | empty when source lacks a date | original |",
        "| description | str | rows with < 15 chars dropped (documented in quality report) | original |",
        "| actual_severity | str | empty when source lacks it; BSEE derived from fatality/injury counts | original / inferred (BSEE) |",
        "| date_closed | str | always empty — no source provides it | empty |",
        "| status | str | always empty — no source provides it | empty |",
        "| observation_date | str | always empty — no source provides it | empty |",
        "| location_detail | str | empty when source lacks it | original |",
        "",
        "## Output fields (computed by the existing engine)",
        "",
        "All outputs are produced by `backend/app/services/analysis_pipeline."
        "analyze_report(description, use_llm=False)` — the same deterministic"
        " engine the web app uses (rule matching + multilingual layer +"
        " risk scoring; no LLM, no random templates). They are therefore"
        " **inferred** values and are always listed in `inferred_fields`.",
        "",
        "| field | engine source | meaning |",
        "|---|---|---|",
        "| equipment | information_extractor.extract_equipment | lexicon-matched equipment terms |",
        "| hazard | extract_hazards | primary hazard from matched indicators / hazard vocabulary |",
        "| barrier_failure | extract_barrier_failures | failed safety barriers (negation-aware) |",
        "| lsr | rule_classifier.classify_rule | mapped Life-Saving Rule |",
        "| sif_potential | risk_scorer.assess | 1 = SIF precursor detected, 0 = not |",
        "| priority | risk_scorer.assess | HIGH / MEDIUM / LOW additive score |",
        "| potential_severity | matched indicator consequence | e.g. fatality / serious injury |",
        "| precursor | matched indicator phrases (`evidence`) | the exact report phrases the engine flagged |",
        "| sif_probability | risk_scorer confidence | 0-1 confidence of the SIF verdict |",
        "| reason | build_explanation | grounded, explainable rationale |",
        "| suggested_immediate_action | narrative.suggest_actions | corrective-action checklist |",
        "| short_summary | narrative.build_summary | plain-language summary |",
        "",
        "## Provenance columns",
        "",
        "| column | meaning |",
        "|---|---|",
        "| source_name | msha / osha_summary / osha_abstract / bsee |",
        "| source_file | originating file (or 'reconstructed' for abstract set 3) |",
        "| inferred_fields | comma-separated canonical fields that are model- or heuristic-derived on this row |",
        "| model_tag | engine tag (rules-v1) |",
        "| languages | languages detected in the description |",
        "| description_len | character length of the cleaned description |",
        "",
    ]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "data_dictionary.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["extract", "analyze", "split", "all"],
                    default="all")
    ap.add_argument("--target", type=int, default=TARGET)
    args = ap.parse_args()

    started = time.time()

    if args.phase in ("extract", "all"):
        extracted, abs_counts, bsee_notes = extract_all()
        for name, rows in extracted.items():
            _write_cache(f"extracted_{name}.csv", rows)
        mapping_doc = _canonical_mapping_doc()
        quality_doc, summary = _write_quality_report(extracted, abs_counts, bsee_notes)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / "column_mapping.md").write_text(mapping_doc, encoding="utf-8")
        (REPORTS_DIR / "data_quality_report.md").write_text(quality_doc, encoding="utf-8")
        print("wrote reports: column_mapping.md, data_quality_report.md")
        print(json.dumps(summary, indent=2))
        if args.phase == "extract":
            return

    if args.phase in ("analyze", "all"):
        extracted = {
            name: _load_cache(f"extracted_{name}.csv")
            for name in ("msha", "osha_summary", "osha_abstract", "bsee")
        }
        if not all(extracted.values()):
            raise SystemExit("extracted caches missing — run --phase extract first")
        run_analyze(extracted, target=args.target)

    if args.phase in ("split", "all"):
        analyzed = _load_cache("analyzed.csv")
        if not analyzed:
            raise SystemExit("analyzed cache missing — run --phase analyze first")
        result = run_split(analyzed)
        _write_data_dictionary()
        print("split summary:", json.dumps(result, indent=2))
        print(f"total elapsed {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()