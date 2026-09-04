# Column mapping — real source files to canonical schema

Every canonical field below is either **original** (read directly from a source
column), **derived** (computed from source columns by a documented heuristic and
flagged `inferred` in the row provenance), or **empty** (the source does not
provide it — it is never fabricated).

## Canonical schema

**Inputs (11):** report_id, incident_id, report_type, site_name, activity, date_reported, description, actual_severity, date_closed, status, observation_date, location_detail

**Outputs (12, computed by the existing engine from the description):** equipment, hazard, barrier_failure, lsr, sif_potential, priority, potential_severity, precursor, sif_probability, reason, suggested_immediate_action, short_summary

**Provenance:** source_name, source_file, inferred_fields, model_tag, languages, description_len

## msha (OSHA Dataset 1)

| canonical field | source column(s) | handling |
|---|---|---|
| report_id | `MINE_ID + AI_DT + DOCUMENT_NO + seq` | composite key |
| incident_id | `MINE_ID | AI_DT | DOCUMENT_NO` | one row per accident normally; groups multi-injury rows of one event |
| report_type | `(constant)` | MSHA mine accident — source is the MSHA accident/injury table |
| site_name | `OPERATOR_NAME (fallback CONTROLLER_NAME)` | original |
| activity | `AI_ACTY_DESC` | original |
| date_reported | `AI_DT` | accident date, original |
| description | `AI_NARR` | accident narrative; empty values dropped |
| actual_severity | `INJ_DEGR_DESC` | original (e.g. Fatal / Nonfatal) |
| date_closed | `(none)` | left empty — not present in source |
| status | `(none)` | left empty |
| observation_date | `(none)` | left empty |
| location_detail | `UG_LOCATION (+ FIPS_STATE_CD in cache)` | original |

## osha_summary (OSHA Dataset 2)

| canonical field | source column(s) | handling |
|---|---|---|
| report_id | `SUMMARY_NR` | original |
| incident_id | `SUMMARY_NR` | original |
| report_type | `(constant)` | OSHA incident summary |
| site_name | `(none)` | left empty |
| activity | `(none)` | left empty |
| date_reported | `EVENT_DATE` | original |
| description | `EVENT_DESC` | headline text; ABSTRACT_TEXT is empty for these rows |
| actual_severity | `FATALITY` | 'X' mapped to Fatality, else empty |
| date_closed | `(none)` | left empty |
| status | `(none)` | left empty |
| observation_date | `(none)` | left empty |
| location_detail | `(none)` | left empty (STATE_FLAG/SIC_LIST kept in cache) |

## osha_abstract (OSHA abstract set 3)

| canonical field | source column(s) | handling |
|---|---|---|
| report_id | `SUMMARY_NR` | original |
| incident_id | `SUMMARY_NR` | original |
| report_type | `(constant)` | OSHA fatality narrative |
| site_name | `(none)` | left empty (extractable from text by the pipeline) |
| activity | `(none)` | left empty |
| date_reported | `(none)` | left empty (the narrative mentions dates in free text) |
| description | `ABSTRACT_TEXT grouped by SUMMARY_NR, sorted by LINE_NR` | RECONSTRUCTED before the row is treated as a report |
| actual_severity | `(constant)` | Fatality — this file is the OSHA fatality narrative set |
| date_closed | `(none)` | left empty |
| status | `(none)` | left empty |
| observation_date | `(none)` | left empty |
| location_detail | `(none)` | left empty |

## bsee (cy-2021/2023/2024 xlsx)

| canonical field | source column(s) | handling |
|---|---|---|
| report_id | `SN_EV_MASTERS` | original |
| incident_id | `SN_EV_MASTERS` | original |
| report_type | `(constant)` | BSEE offshore incident |
| site_name | `Operator Name` | original |
| activity | `operation flag columns (Production/Drilling/...)` | DERIVED — Y-flagged operation mapped to label, flagged inferred |
| date_reported | `Date` | original |
| description | `Incident Summary` | original free text |
| actual_severity | `Operator/Contractor Fatalities + injury count columns` | DERIVED — Fatality if any fatality count > 0, else Injury if any injury count > 0, else empty; flagged inferred |
| date_closed | `(none)` | left empty |
| status | `(none)` | left empty |
| observation_date | `(none)` | left empty |
| location_detail | `Structure Name (fallback Area Name + Block)` | original |

## report_type honesty note

The UA / UC / Near-miss taxonomy is NOT present in any of these four
sources, so `report_type` carries the true source label instead (MSHA mine accident / OSHA incident summary / OSHA fatality narrative / BSEE offshore incident). No near-miss classification is
fabricated.

## Compressed xlsx files

`compressed_cy-*-excel-spreadsheet.xlsx` duplicate the uncompressed
sheets (identical sharedStrings; sheet XML differs by ~1 KB of
metadata). They are skipped.