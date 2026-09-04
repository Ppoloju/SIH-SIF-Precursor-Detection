# Data dictionary — canonical fields

Every row in `data/processed/{train,validation,test}.csv` has the same canonical schema. Values are either **original** (read from a source column), **empty** (the source did not provide the field — never fabricated), or **inferred** (derived by the documented engine / a documented heuristic). The `inferred_fields` column lists, per row, every canonical field whose value is model-derived or heuristic-derived.

## Input fields

| field | type | missingness handling | original vs inferred |
|---|---|---|---|
| report_id | str | composite from source keys (see column mapping) | original |
| incident_id | str | grouping key; fragments of one event never cross splits | original |
| report_type | str | constant per source — never UA/UC/Near-miss (not in these datasets) | original |
| site_name | str | empty when source lacks it (OSHA sets) | original |
| activity | str | empty when source lacks it; BSEE value mapped from Y-flagged operation columns | original / inferred (BSEE) |
| date_reported | str (ISO) | empty when source lacks a date | original |
| description | str | rows with < 15 chars dropped (documented in quality report) | original |
| actual_severity | str | empty when source lacks it; BSEE derived from fatality/injury counts | original / inferred (BSEE) |
| date_closed | str | always empty — no source provides it | empty |
| status | str | always empty — no source provides it | empty |
| observation_date | str | always empty — no source provides it | empty |
| location_detail | str | empty when source lacks it | original |

## Output fields (computed by the existing engine)

All outputs are produced by `backend/app/services/analysis_pipeline.analyze_report(description, use_llm=False)` — the same deterministic engine the web app uses (rule matching + multilingual layer + risk scoring; no LLM, no random templates). They are therefore **inferred** values and are always listed in `inferred_fields`.

| field | engine source | meaning |
|---|---|---|
| equipment | information_extractor.extract_equipment | lexicon-matched equipment terms |
| hazard | extract_hazards | primary hazard from matched indicators / hazard vocabulary |
| barrier_failure | extract_barrier_failures | failed safety barriers (negation-aware) |
| lsr | rule_classifier.classify_rule | mapped Life-Saving Rule |
| sif_potential | risk_scorer.assess | 1 = SIF precursor detected, 0 = not |
| priority | risk_scorer.assess | HIGH / MEDIUM / LOW additive score |
| potential_severity | matched indicator consequence | e.g. fatality / serious injury |
| precursor | matched indicator phrases (`evidence`) | the exact report phrases the engine flagged |
| sif_probability | risk_scorer confidence | 0-1 confidence of the SIF verdict |
| reason | build_explanation | grounded, explainable rationale |
| suggested_immediate_action | narrative.suggest_actions | corrective-action checklist |
| short_summary | narrative.build_summary | plain-language summary |

## Provenance columns

| column | meaning |
|---|---|
| source_name | msha / osha_summary / osha_abstract / bsee |
| source_file | originating file (or 'reconstructed' for abstract set 3) |
| inferred_fields | comma-separated canonical fields that are model- or heuristic-derived on this row |
| model_tag | engine tag (rules-v1) |
| languages | languages detected in the description |
| description_len | character length of the cleaned description |
