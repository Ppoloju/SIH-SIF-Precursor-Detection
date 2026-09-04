# SIF Precursor Detection — Backend

FastAPI backend for the SIH SIF Precursor Detection prototype (Problem Statement 26165, Oil India Limited).

## Run

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

On first start the app creates tables and seeds **45 clearly-labeled synthetic demo reports** plus the Life-Saving Rule taxonomy. Set `SEED_DEMO_DATA=0` to keep an empty database for real imports (or delete `sif_detection.db` and restart to reseed).

## Database

The app runs on whatever `DATABASE_URL` points at (see `.env.example` at the repo root):

- **PostgreSQL** (recommended real flow) — Supabase connection string, or local:
  `docker compose up -d` in the repo root, then `DATABASE_URL=postgresql+psycopg://sif:sif@localhost:5432/sif_detection`. Requires `pip install "psycopg[binary]"`.
- **SQLite** (zero-setup demo) — default `sqlite:///./sif_detection.db`.

Schema is created automatically on startup; additive migrations run for pre-existing databases.

## Layout

```
app/
├── main.py                  # entrypoint (lifespan: init db + seed demo data)
├── config.py                # settings from env (see .env.example at repo root)
├── api/
│   ├── reports.py           # analyze / create / list / get / reanalyze (+ similar)
│   ├── ingest.py            # dataset upload (CSV/JSON/XLSX) preview + import
│   ├── review.py            # PATCH /api/reports/{id}/review  (HSE review)
│   ├── analytics.py         # overview, rules, sites, activities, barriers, patterns
│   ├── feedback.py          # /api/feedback/summary + /api/feedback/train
│   └── evaluation.py        # /api/evaluation (golden-set metrics)
├── services/
│   ├── safety_lexicon.py    # Life-Saving Rule profiles + vocabularies (configurable)
│   ├── sif_detector.py      # negation-aware indicator detection + evidence
│   ├── multilingual.py      # Hindi/Bengali/Assamese lexicon + language detection
│   ├── rule_classifier.py   # Life-Saving Rule mapping
│   ├── information_extractor.py  # activity/hazard/barrier/equipment extraction
│   ├── risk_scorer.py       # transparent AI-assisted priority (prototype)
│   ├── narrative.py         # plain-language summary + corrective-action templates
│   ├── similarity.py        # similar-report search (text overlap + shared concepts)
│   ├── adaptive.py          # feedback capture, agreement metrics, learned signals
│   ├── evaluation.py        # golden-set SIF + per-rule metrics
│   ├── analysis_pipeline.py # orchestrates the hybrid pipeline
│   ├── ingest.py            # generic dataset parsing + column auto-mapping
│   └── llm.py               # optional Groq/Llama refinement (validated, graceful)
├── models/                  # SQLAlchemy entities (reports, analyses, reviews,
│                            #   feedback, training_runs, life_saving_rules, embeddings)
├── schemas/                 # Pydantic v2 schemas
└── data/                    # demo dataset, rule taxonomy, golden evaluation set
scripts/
├── verify_engine.py         # dev check of detection agreement on the demo set
├── smoke_api.py             # end-to-end API smoke test
├── verify_ingest.py         # generic-dataset ingestion end-to-end check
└── evaluate.py              # golden-set evaluation (table / --json)
```

## AI-depth features

- **Multilingual detection** — `services/multilingual.py` holds curated phrase lexicons for Hindi (Devanagari + roman Hinglish), Bengali (native + roman) and Assamese (native + roman). Non-English failure phrases map to the **same canonical Life-Saving Rules**; evidence stays the literal original text; `detect_languages` records which languages/scripts a report uses (stored in `analyses.languages`).
- **Summary + suggested actions** — every analysis carries a three-part plain-language `summary` (what happened / why it matters / next step) and a `suggested_actions` checklist built deterministically from the rule profile + failed barriers (`services/narrative.py`); the optional LLM may rephrase them in the report's own language.
- **Similar reports** — `services/similarity.py` ranks reports by token overlap **plus** shared rule/hazard/barrier/activity (works across English and Indic text). Similar entries are returned with report detail, on dashboard high-priority rows (up to 3) and after ad-hoc analysis.
- **Feedback → retraining loop** — each HSE review writes a labeled row to `feedback` (AI snapshot + human decision). `POST /api/feedback/train` recomputes model↔human precision/recall/F1, mines *learned signals* (phrases from reports where reviewers disagreed), stores a `training_runs` row, and applies the signals to later analyses (evidence quote + confidence nudge, model tagged `rules-v1+tuned`; verdicts never auto-flip).
- **Evaluation harness** — `app/data/golden_set.py` holds 35 labeled reference reports (English/Hindi/Bengali/Assamese); `services/evaluation.py` computes SIF classification + per-rule metrics deterministically in-process. `GET /api/evaluation` powers the frontend Evaluation page.

## Optional AI services

- **LLM refinement (Llama via Groq):** set `GROQ_API_KEY`. Output is Pydantic-validated; any failure falls back to the deterministic result.
- **Embeddings / scikit-learn:** optional extras (commented in `requirements.txt`) for deeper ML once labeled data exists — the shipped similar-report search and feedback loop are dependency-free.
- **Supabase PostgreSQL:** set `DATABASE_URL`; otherwise local SQLite is used so the demo runs out of the box.

## Design notes

- Deterministic rule + multilingual layers always run; optional AI services can never crash the pipeline.
- Evidence is always text quoted from the report — the engine cannot invent it.
- Learned reviewer signals quote real report phrases and tune confidence/evidence only — they never flip a SIF verdict on their own.
- Barrier/priority/hazard outputs are prototype-level and require HSE/OIL validation.
