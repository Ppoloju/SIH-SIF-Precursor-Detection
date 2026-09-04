# Data quality report — real source files

Generated 2026-09-04 19:28:56 UTC by `backend/scripts/build_real_dataset.py`.

## Raw row counts

| source | raw rows | rows with non-empty description |
|---|---|---|
| msha | 740390 | 274565 |
| osha_summary | 165801 | 165799 |
| osha_abstract | 165794 | 165793 |
| bsee | 2777 | 2777 |

## OSHA abstract set 3 — reconstruction counts

- line rows in source: **1151160**
- unique SUMMARY_NR (reconstructed reports): **165794**
- multi-line narratives: **164615**
- single-line narratives: **1179**
- narratives with zero text after reconstruction: **1**
- longest narrative (lines): **110**

## BSEE xlsx rows

- cy-2021: 773 rows
- cy-2023: 959 rows
- cy-2024: 1047 rows

## Description length distribution (non-empty descriptions)

| source | n | median chars | mean chars | p90 chars | max chars |
|---|---|---|---|---|---|
| msha | 274565 | 175 | 188 | 331 | 610 |
| osha_summary | 165799 | 49 | 48 | 60 | 60 |
| osha_abstract | 165793 | 418 | 514 | 940 | 8833 |
| bsee | 2777 | 780 | 956 | 1775 | 8838 |

## Missingness of canonical INPUT fields (non-empty description rows)

| source | report_id | site | activity | date | actual_severity | location |
|---|---|---|---|---|---|---|
| msha | 0 | 721 | 0 | 0 | 0 | 0 |
| osha_summary | 0 | 165799 | 165799 | 0 | 93344 | 165799 |
| osha_abstract | 0 | 165793 | 165793 | 165793 | 0 | 165793 |
| bsee | 0 | 0 | 0 | 19 | 2193 | 1 |

## Extraction notes

- OSHA Dataset 2: `ABSTRACT_TEXT` is empty on every row; `EVENT_DESC` is populated for all of them and is used as the description.
- OSHA Dataset 1: `AI_NARR` is empty for a large share of rows; those rows are counted above and excluded from candidates.
- BSEE `actual_severity` is derived from fatality/injury counts and is flagged `inferred` in row provenance.
