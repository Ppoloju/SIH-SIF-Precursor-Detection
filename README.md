# SIH SIF Precursor Detection

**AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in OIL's Unsafe-Act / Unsafe-Condition and Near-Miss Reports**

Smart India Hackathon 2026 · Problem Statement **26165** · **Oil India Limited** · Theme: **Smart Automation**

> Turning free-text safety reports into explainable, actionable safety intelligence.

---

## Prototype Status — Please Read

This is a **prototype for SIH demonstration**. It uses **synthetic demo data** (never real OIL data), an **AI-assisted prototype priority assessment** (not an official OIL risk score), and **requires HSE/OIL validation** before any operational use. No model accuracy, official classification, or OIL statistics are claimed.

---

## Problem

OIL collects large volumes of safety reports through its HSSE platform — Unsafe Acts (UA), Unsafe Conditions (UC), Near-Misses and Incidents — much of it free text. A report that **looks low-severity may still contain conditions with genuine Serious Injury or Fatality potential**. Manual periodic triage makes it hard to find these precursors early and to see where the same problems recur.

## What it does

An **AI Safety Early-Warning & SIF Precursor Intelligence Platform** that screens every report the moment it arrives and lets HSE experts focus where fatal potential is highest. It is an early-warning decision-support layer — it does not replace OIL's HSE process or experts. Concretely, the platform:

1. **Ingests any dataset** — CSV / Excel / JSON / TSV / TXT with any column names. Headers are auto-mapped by synonym scoring (preview before import, overridable), dates are parsed across formats, and imports run as background jobs whose progress is persisted and visible live. Rows whose text already exists are skipped and reported as duplicates — nothing is stored twice silently.
2. **Analyses every report** with a hybrid, explainable NLP pipeline: SIF-potential detection with **verbatim quoted evidence** (English + Hindi + Bengali + Assamese, native script and romanised), then structured extraction of hazard, potential consequence, barrier failure, activity, location, equipment and unsafe type.
3. **Maps each report to one of the ten canonical Life-Saving Rules** — Work Authorization, Energy Isolation, Bypassing Safety Controls, Confined Space Entry, Working at Height, Safe Mechanical Lifting, Toxic Gas Safety, Driving Safety, Line of Fire, Hot Work Safety — with per-condition `breached / in_place / not_verifiable` verdicts and the exact wording each was inferred from. When neither the file nor the text states a rule, it is estimated from the file's hazard/activity values and the derivation is stated honestly.
4. **Is honest about every field.** Each report shows a *Field Coverage* panel: **Source file** (authoritative, used as-is), **AI text analysis** (filled only when the file is silent), or **Not stated** (never fabricated). File-provided values win over AI extraction, which is retained for reference only. Uncertainty notes surface any inferred or learned value, and the model tag (`rules-v1`, `rules-v1+llm`, `rules-v1+tuned`) records provenance.
5. **Assigns a transparent, explainable priority** (HIGH / MEDIUM / LOW) from four stored factors — matched indicators (capped at 3), consequence severity (0–2), people exposure (0–1), barrier failure (0–1); HIGH ≥ 5, MEDIUM ≥ 3, else LOW. Every report shows a "how it was calculated" breakdown. Confidence = `min(0.97, 0.62 + 0.11·indicators + 0.05·severity)`. This is a prototype methodology, not an official OIL risk score.
6. **Reads multilingual reports** — Hindi, Bengali and Assamese (Devanagari/Bengali script and romanised Hinglish/Benglish) map the same explicit failure phrases to the same rules, evidence stays in the original words, and detected languages are shown on the result. *A big differentiator for OIL's real, code-mixed reports.*
7. **Links every report to history** — "N similar" past reports (text overlap + shared rule / hazard / barrier / activity, with the shared fields shown so the score is auditable) appear on the dashboard, the report page and after each fresh analysis. When a current report matches a case another site already **verified** (ideally with action notes), that case is highlighted as the reference (site A → site B learning). Near-copies (similarity ≥ 0.88) are flagged `duplicate_of` with a compare link.
8. **Finds recurring patterns** — co-occurrence grouping of ≥ 2 SIF-potential reports by rule+activity / rule+barrier / hazard+activity, always backed by the real member reports: click a pattern to open them in the Reports registry, and a *How patterns are found* popup documents the mapping criteria.
9. **Keeps dashboards honest** — KPIs, weekly SIF trend (the same data switchable between area / line / bar / bar+line), SIF precursor density (SIF-potential ÷ total) with a counts ⇄ density toggle, Life-Saving-Rule distribution, site / activity / barrier-failure analytics — raw counts labeled separately from density, nothing fabricated. Every view exports to CSV with the current filters.
10. **Separates the HSE Reviewer from the everyday user** — a dedicated **HSE Review** workspace (`/review`) with a live pending-count badge in the nav. Reviewers see only what still needs a human decision, click **Verify as SIF / Not SIF** once, correct priority or rule, and leave comments. Clear badges distinguish *Needs HSE review · HSE verified · HSE reviewed · HSE edited · Rejected · not SIF*.
11. **Closes the loop with feedback → retraining** — every review decision is stored as a labelled example; *Train on reviewed labels* recomputes model↔human agreement (precision / recall / F1), mines the surface phrases behind disagreements and applies them as weighted, review-flagged signals to future analyses. A learned keyword alone never flips a verdict.
12. **Measures itself** — the live **Model Evaluation** page runs two benchmarks end-to-end (see [Evaluation](#evaluation)): the deterministic golden-set harness (35 hand-labelled reports, P/R/F1 1.000, multilingual 19/19) with a stratified k-fold stability check, and a statistical ML benchmark — stratified 5-fold CV over a 500-report dataset (Multinomial Naive Bayes, Logistic Regression, Linear SVM vs the rule engine baseline, F₂-weighted).
13. **Has a clean app shell** — fixed **left sidebar** on desktop (Work: Dashboard · HSE Review · Reports · Analyze · Import Data — Insights: Life-Saving Rules · Recurring Patterns · Site Risk · Activities · Barrier Failures · Model Evaluation), a drawer on mobile, a light/dark toggle in the sidebar footer (and mobile top bar), and a live backend-status indicator.
14. **Degrades gracefully** — the deterministic rules always run: no LLM key means no polish pass, no PostgreSQL means a local SQLite file, and analysis still works offline.

## Architecture

```
┌──────────────────────────────┐
│       Next.js Frontend       │   Dashboard / HSE Review / Analyze /
│   (React + Tailwind + Recharts)  Import Data / Reports / Analytics
│                              │   (Rules, Sites, Activities, Barriers,
│                              │   Patterns, Evaluation)
└──────────────┬───────────────┘
               │ REST API (JSON + multipart uploads)
               ▼
┌──────────────────────────────┐
│        FastAPI Backend       │
│ Reports / Ingest / Analytics │
│         / Review             │
└──────────────┬───────────────┘
               │
       ┌───────┼─────────┐
       ▼       ▼         ▼
   Rules    NLP/ML    LLM (optional,
   engine   extraction  Groq/Llama)
       │       │
       └───────┼─────────┘
               ▼
┌──────────────────────────────┐
│        PostgreSQL            │
│ (local Docker or SQLite;     │
│  SQLite fallback for demo)   │
│ reports / analyses / reviews │
│ life_saving_rules / embeddings
└──────────────────────────────┘
```

### AI / NLP design — hybrid, not LLM-everywhere

| Layer | Purpose |
|---|---|
| **Rules** | Deterministic, negation-aware baseline detection of obvious SIF indicators (energy isolation, LOTO, gas testing, fall protection…). Always available, fully explainable. |
| **Multilingual layer** | Understands Hindi, Bengali and Assamese safety reports — native script and romanised — mapping the same explicit failure phrases to the same Life-Saving Rules and quoting the original text as evidence. |
| **NLP / ML** | Structured extraction (activity, hazard, barrier, equipment, unsafe act/condition). Statistical ML slots in here via the evaluation benchmark and, when labelled OIL data becomes available, for classification. |
| **Similarity** | Similar-report linking from text overlap + shared rule / hazard / barrier / activity — no external model required, works across languages. |
| **LLM (Llama via Groq, optional)** | Polish only: rephrases explanations / summaries into the report's language — **Pydantic-validated, with graceful fallback** to the deterministic result when unavailable or invalid. |
| **Feedback → retraining** | Every HSE review is stored as a labeled example; *Train on reviewed labels* measures model↔human agreement and learns signals from the disagreements, which tune future analyses. |
| **Human** | HSE professionals make the final call through the dedicated review workflow. |

## Algorithms Used

Everything below runs offline, is deterministic and explainable — the optional LLM only polishes output.

| # | Algorithm / method | What it does | Where it lives |
|---|---|---|---|
| 1 | **Negation-aware rule matching** | Keyword + phrase patterns per Life-Saving Rule, matched with negation detection ("without isolation", "no permit", "missing guard") so a control that is *present* is not flagged as breached. Quotes the exact evidence phrase. | `safety_lexicon.py`, `sif_detector.py` |
| 2 | **Additive priority scoring** | `score = min(matched_indicators, 3) + severity_bonus(0–2) + people_exposure(0–1) + barrier_failure(0–1)`; HIGH ≥ 5, MEDIUM ≥ 3, else LOW. Confidence = `0.62 + 0.11·indicators + 0.05·severity`, capped at 0.97. The four factors are stored per report and shown as a "how it was calculated" breakdown. | `risk_scorer.py` |
| 3 | **Life-Saving-Rule classification** | Per-condition mapping of the text to each rule's requirements with a `breached / in_place / not_verifiable` verdict and per-condition evidence. | `rule_classifier.py`, `rule_mapper.py` |
| 4 | **Rule estimation from structured fields** | When the file/text gives no Life-Saving Rule signal, the rule is estimated from the file's own hazard/activity values (e.g. hazard "confined space entry" → Confined Space Entry) and the derivation is stated in the uncertainty note. | `ingest.py` (`estimate_rule_from_fields`) |
| 5 | **Language detection (multilingual)** | Script detection for Devanagari / Bengali / Assamese plus romanised Hinglish / Benglish lexicons; the same failure phrases map to the same rules across languages. | `multilingual.py` |
| 6 | **Hybrid similarity linking** | Similar-report score from token overlap (normalised word-level similarity) **plus** shared rule / hazard / barrier / activity concept bonuses (capped low so genuine near-copies outscore distinct-but-related precursors). Scores are shown with the shared fields on the report page. | `similarity.py` |
| 7 | **Duplicate detection** | Import-time text fingerprinting skips identical rows (reported as "Row N → duplicate of RPT-x") and near-copies (similarity ≥ 0.88) are flagged as `duplicate_of` on the report detail. | `ingest.py`, `reports.py` (`DUP_SIMILARITY = 0.88`) |
| 8 | **Feedback → retraining loop** | Every HSE review is stored as a labelled example; "Train on reviewed labels" computes model↔human agreement (precision / recall / F1), mines the surface phrases of disagreements, and applies them as weighted learned signals to future analyses. | `adaptive.py` |
| 9 | **Honest field inference** | Each field is tagged *Source file* (authoritative), *AI text analysis* (inferred), or *Not stated* — the engine never fabricates values; file-provided values are used as-is and the AI extraction is kept for reference. | `ingest.py`, `analysis_pipeline.py` |
| 10 | **Recurring-pattern mining** | Co-occurrence grouping of ≥ 2 SIF-potential reports by rule+activity / rule+barrier / hazard+activity, backed by the real member reports and clickable into the filtered registry. | `analytics.py` (`/patterns`) |
| 11 | **Trend & density analytics** | Weekly trend bucketing; SIF precursor density = SIF-potential ÷ total reports; week-over-week deltas; chart types area / line / bar / bar+line on the same data. | `analytics.py`, dashboard |
| 12 | **Golden-set evaluation + stability CV** | Holdout golden set (35 hand-labelled reports across EN/HI/BN/AS) with per-class and per-rule precision / recall / F1, plus a stratified k-fold stability check (mean ± std and 95% CI over folds stratified by SIF label × language). | `evaluation.py` (`run_evaluation`, `run_kfold_cv`) · page + CLI |
| 13 | **Stratified 5-fold ML benchmark** | Statistical models (Multinomial Naive Bayes, Logistic Regression, Linear SVM) vs the rule-engine baseline over a 500-report dataset, TF-IDF fit inside each fold to prevent leakage, F₂-weighted metrics + decision-threshold sensitivity. | `model_evaluation.py` (`evaluate_sif_models`) · `/api/model/evaluate` |
| 14 | **LLM refinement (optional)** | Llama (Groq) rephrases explanations / summaries / follow-ups with Pydantic-validated output and deterministic fallback when unavailable. | `llm.py` |

## Technology Stack

**Frontend:** Next.js (App Router) · React · Tailwind CSS · Recharts · Lucide React

**Backend:** Python · FastAPI · Pydantic v2 · SQLAlchemy

**AI/NLP:** Rule-based NLP + multilingual lexicons (primary) · Llama via Groq (optional) · scikit-learn / pandas (evaluation benchmark; optional when labeled data is available)

**Database:** PostgreSQL (local Docker or Supabase) with a zero-setup SQLite fallback — one code path, selected by `DATABASE_URL`

**Docs (see also the "Documentation map" below):** `docs/index.html` project showcase with the user flows · `docs/processing.html` data-processing stages and the algorithm behind every output field

## Repository Structure

```
SIH-SIF-Precursor-Detection/
├── frontend/                  # Next.js application
│   ├── app/                   # pages: /, /review (HSE queue), /analyze, /ingest,
│   │                          #   /reports, /reports/[id], /rules, /sites,
│   │                          #   /activities, /barriers, /patterns, /evaluation
│   ├── components/            # nav (sidebar, dark/light toggle), footer, badges,
│   │                          #   analysis-result card, rules-guide popup,
│   │                          #   export button, theme provider
│   └── lib/                   # typed API client, chart palette, export helpers
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint (startup init, health)
│   │   ├── config.py          # settings from env (DB URL, LLM key, CORS)
│   │   ├── api/               # reports, review, ingest, analytics, feedback, evaluation
│   │   ├── services/          # sif_detector, safety_lexicon, multilingual,
│   │   │                      # rule_classifier, rule_mapper, information_extractor,
│   │   │                      # risk_scorer, analysis_pipeline, narrative, similarity,
│   │   │                      # ingest, adaptive (feedback→retrain),
│   │   │                      # evaluation (golden set + k-fold), model_evaluation (ML CV)
│   │   ├── models/            # SQLAlchemy entities + engine/session (reports, analyses,
│   │   │                      #   reviews, feedback, training_runs, life_saving_rules…)
│   │   ├── schemas/           # Pydantic schemas
│   │   └── data/              # life_saving_rules, demo dataset, golden evaluation set,
│   │                          #   oil_hsse_sif_dataset (500 rows for the ML benchmark)
│   ├── scripts/               # evaluate, verify_engine, verify_ingest, smoke_api,
│   │                          #   generate_dataset, clear_database
│   ├── requirements.txt
│   └── README.md
├── docs/
│   ├── index.html             # showcase — what/why + user flows + mock outputs
│   └── processing.html        # deep dive — processing stages + per-field algorithms
├── docker-compose.yml         # local PostgreSQL for the real database flow
├── .env.example
├── .gitignore
└── README.md                  # this run book
```

## Setup

### Prerequisites
- Python 3.11+ and Node.js 18+

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/api/health
- On first start the backend creates the schema automatically and seeds only the ten **Life-Saving-Rule taxonomy** rows. **Demo reports are intentionally not seeded** in this build (`backend/app/data/seed.py`) — the database starts empty and stays empty until you import your own data.
- Default storage is a local **SQLite file** (`backend/sif_detection.db`) so the demo runs with zero setup.

#### Optional: PostgreSQL (the real database flow)

```bash
docker compose up -d                       # starts sif-postgres on :5432 (repo root)
pip install "psycopg[binary]" openpyxl     # PostgreSQL driver + XLSX ingestion
# backend/.env:  DATABASE_URL=postgresql+psycopg://sif:sif@localhost:5432/sif_detection
uvicorn app.main:app --reload --port 8000  # creates the same schema in Postgres
```

The same code path runs against either engine — `/api/health` reports which one is active, and the app footer shows it truthfully.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:3000
```

The frontend reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

> Appearance: use the **sun / moon toggle** in the sidebar footer (or the mobile top bar) to switch between light and dark mode. The choice is remembered in the browser; the first visit follows the operating-system preference.

### Viewing the documentation

```bash
# Just open in a browser:
open docs/index.html             # showcase — flows, outputs, architecture
open docs/processing.html        # how data is processed + which algorithm decides each field
```

## Documentation map

The three documents are scoped so nothing is duplicated:

| Document | Scope |
|---|---|
| **README.md** (this file) | Run book — problem, feature set, setup, environment, API, evaluation, limitations |
| **docs/index.html** | Showcase — what the product does, the two user flows, mock outputs, dashboard, architecture |
| **docs/processing.html** | Deep dive — the 9-stage processing pipeline and a field-by-field table of the algorithm that decides each output |

## Environment Variables (`.env.example`)

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | No | Optional LLM refinement (Llama via Groq). Without it, rule-based analysis runs. |
| `DATABASE_URL` | No | PostgreSQL URL (local Docker or Supabase). Defaults to local SQLite (`sqlite:///./sif_detection.db`) when unset. |
| `NEXT_PUBLIC_API_URL` | No | Frontend → backend base URL. Defaults to `http://localhost:8000`. |
| `SEED_DEMO_DATA` | No | Accepted for compatibility but **currently ignored**: demo seeding is disabled in code so the database always contains only imported data. |

Never commit real credentials. Never commit a `.env` file.

## Ingesting Your Own Dataset (any format)

The platform is **dataset-agnostic** — it analyzes any safety-report dataset, not just a fixed schema. The full flow:

```
Dataset file (CSV / Excel / JSON / TSV / TXT, any columns)
        ↓  auto-detect column mapping (synonym-scored, preview first)
Preview: which column is the report text / date / site / activity?
        ↓  (adjust mapping if needed)
Each row → normalized → duplicate fingerprint → SIF pipeline
         (detect → evidence → hazard → barrier → rule → priority)
        ↓
Database: report + analysis stored (source label kept) — progress visible
        ↓
Dashboard, sites, activities, barriers & patterns update automatically
        ↓
HSE review of any flagged report → labeled example → retraining
```

Import from the **Import Data** page (left sidebar) or directly via the API:

```bash
# Preview without writing anything
curl -F "file=@incidents.csv" http://127.0.0.1:8000/api/ingest/file/preview

# Import (auto column mapping)
curl -F "file=@incidents.csv" http://127.0.0.1:8000/api/ingest/file

# Explicit mapping override:  {"text": "Narrative", "date": "When", "site": null}
curl -F "file=@incidents.csv" \
     -F 'field_mapping={"text": "Narrative", "date": "When"}' \
     http://127.0.0.1:8000/api/ingest/file

# Raw JSON rows (APIs / scripts)
curl -X POST http://127.0.0.1:8000/api/ingest/rows -H "Content-Type: application/json" \
  -d '{"rows": [{"Description": "Welder did hot work without a gas test.", "Location": "Plant B"}]}'
```

Column synonyms are auto-detected (e.g. *Report / Description / Narrative / Observation / What happened* → text; *Site / Location / Plant / Area / Work location* → site; *Date of occurrence / Reported on* → date; *Activity / Nature of work / Type of job* → activity; *Type / Category* → report type). Dates are parsed across common formats. Rows with no explicit metadata are still fully analyzed from free text — nothing requires a particular schema.

`backend/scripts/verify_ingest.py` runs the whole flow against a deliberately foreign-format CSV.

## Datasets in the repository

| File | Rows | Used for |
|---|---|---|
| `backend/app/data/demo_reports.py` | 45 synthetic, invented reports | Offline scripts only (`scripts/verify_engine.py`, `scripts/generate_dataset.py`). **Not seeded at startup** in this build — the running database stays empty until you import. |
| `backend/app/data/golden_set.py` | 35 hand-labelled reports (EN / HI / BN / AS) | Deterministic engine benchmark — SIF + per-rule precision / recall / F1 (see Evaluation). |
| `backend/app/data/oil_hsse_sif_dataset.csv` | 500 labelled SIF reports | Statistical ML benchmark — stratified 5-fold CV of Naive Bayes / Logistic Regression / Linear SVM vs the rule baseline. |

## API Overview

```
GET    /api/health                  # status + active database engine
POST   /api/reports/analyze         # analyze (store=true/false)
POST   /api/reports                 # create + analyze + store
GET    /api/reports                 # list (filters: site, activity, priority, rule,
                                    #   status, sif, q, source, hazard, barrier)
GET    /api/reports/counts          # quick counts: total / pending / verified / rejected / failed
GET    /api/reports/{id}            # full detail incl. analysis + review + similar + duplicate_of
POST   /api/reports/{id}/reanalyze  # re-run pipeline, update stored analysis
PATCH  /api/reports/{id}/review     # HSE review decision
POST   /api/ingest/file/preview     # upload dataset, preview mapping (no writes)
POST   /api/ingest/file             # start import job for an uploaded file
POST   /api/ingest/rows             # start import job for raw JSON rows
GET    /api/ingest/jobs/{id}        # poll job progress (persisted in the DB)
GET    /api/ingest/jobs             # recent import jobs
GET    /api/analytics/overview      # KPIs + trend + recent high-priority
GET    /api/analytics/life-saving-rules
GET    /api/analytics/sites
GET    /api/analytics/activities
GET    /api/analytics/barriers
GET    /api/analytics/patterns
GET    /api/evaluation              # golden-set metrics + k-fold stability + ML CV payload
GET|POST /api/model/evaluate        # run the stratified 5-fold ML benchmark
GET    /api/feedback/summary        # reviewed-label counts + latest training run
POST   /api/feedback/train          # train on reviewed labels (metrics + learned signals)
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/reports/analyze \
  -H "Content-Type: application/json" \
  -d '{"report_text": "During maintenance, the technician started work on a pipeline without properly isolating the energy source.", "store": false}'
```

```json
{
  "sif_potential": true,
  "confidence": 0.78,
  "priority": "HIGH",
  "hazard": "Uncontrolled energy",
  "life_saving_rule": "Energy Isolation",
  "activity": "Maintenance",
  "barrier_failure": ["Energy Isolation / LOTO"],
  "evidence": ["without properly isolating"],
  "explanation": "The report states: \"…\". This is associated with uncontrolled energy. …",
  "languages": ["en"],
  "summary": "What happened — …\n\nWhy it matters — …\n\nNext step — …",
  "suggested_actions": ["Verify isolation and lockout/tagout controls before maintenance begins.", "…"]
}
```

### Multilingual reports work the same way

```bash
curl -X POST http://127.0.0.1:8000/api/reports/analyze -H "Content-Type: application/json" \
  -d '{"report_text": "Contractor ne bina gas test ke tank ke andar kaam shuru kar diya aur koi attendant nahi tha.", "store": false}'
# => life_saving_rule: "Confined Space Entry", languages: ["en", "hi-latn"], evidence: ["bina gas test"]
```

Also handles Devanagari (`गैस टेस्ट के बिना`), Bengali (`গ্যাস টেস্ট করা হয়নি`, roman "gas test chara") and Assamese (`গেছ টেষ্ট নকৰাকৈ`) phrases — try the Hindi / Bengali example chips on the Analyze page.

## Evaluation

The **Model Evaluation** page (`/evaluation`) runs two distinct, complementary benchmarks. The CLI reproduces both:

```bash
cd backend
python scripts/evaluate.py --cv 5   # golden-set metrics + stratified k-fold stability table
python scripts/evaluate.py --json --cv 5
```

### 1. Deterministic Golden-Set Engine Benchmark (35 multilingual cases)

- A hand-labelled reference set of 35 incident reports (`backend/app/data/golden_set.py`) covering all ten Life-Saving Rules across English, Hindi (Devanagari & Hinglish), Bengali and Assamese.
- Verifies the **rule-based + multilingual engine** (deterministic, offline): regional phrase patterns and script translations fire the right rules and detect SIF potential without any external LLM.
- Current results: SIF precision / recall / F1 = **1.000**, multilingual cases **19/19**, runtime ≈ **20 ms**.
- A **stratified 5-fold stability check** (folds dealt by SIF label × language) reports mean ± std and a 95% CI over fold compositions, so the numbers are checked for stability — not a single lucky split.

### 2. Stratified 5-Fold ML Cross-Validation (500-report dataset)

- A stratified 5-fold CV suite over `backend/app/data/oil_hsse_sif_dataset.csv` (500 reports).
- Evaluates **statistical models** — Multinomial Naive Bayes, Logistic Regression, Linear SVM — against the **rule-engine baseline**, isolating TF-IDF vectorization inside each fold to prevent data leakage and reporting per-fold precision, recall, F1 and safety-critical **F2**, plus a decision-threshold sensitivity analysis. Served by `GET/POST /api/model/evaluate`.

> **Key distinction:** the golden set (35 cases) evaluates rule-based multilingual coverage; the 5-fold CV (500 reports) evaluates statistical ML algorithm performance.

- **Human agreement** — reviewed reports become labeled examples; `POST /api/feedback/train` (or the *Train on reviewed labels* button) recomputes AI↔HSE agreement and mined signals. The same k-fold seams become train/test splits for the adaptive signals once enough reviewed feedback accumulates.
- Recall matters most: missing a genuine SIF precursor is more serious than an extra false alert. **No claim of accuracy on real OIL data is made** — metrics describe the deterministic rules on the in-repo reference set and require HSE-validated labels to generalize.

### Validating with real data (TSTR roadmap)

The golden set was authored against the same rule lexicon, so perfect scores there prove *consistency*, not *real-world generalization*. The planned external validation ladder (documented here so reviewers see the intent):

1. **TSTR (Train-Synthetic-Test-Real)** — generate synthetic rows from a train split only, train, and evaluate on a *real* holdout (e.g. a manually labeled slice of OSHA / MSHA / Canada-OHS incident text). Synthetic-trained F1 within ~90–95% of real-trained F1 ⇒ the synthetic data has utility.
2. **Statistical fidelity** — Kolmogorov–Smirnov over numeric fields (exposure/risk scores), chi-square / total-variation distance over categorical fields (rule, activity, barrier), correlation-matrix and Jensen–Shannon comparisons over feature pairs between synthetic and real sets.
3. **Discriminator test** — train a simple classifier on the real-vs-synthetic task; accuracy near 50% means the synthetic distribution is hard to distinguish; well above chance points to which features to re-generate.
4. **Near-duplicate audit** — cosine similarity on embeddings plus rule+activity+barrier tuple frequencies, to ensure generation adds diversity rather than near-copies.
5. **Human expert review** — HSE scores a sample of synthetic reports for plausibility and correct rule mapping (extends the existing feedback loop to generation).

## Limitations

- Data in the repository is synthetic; the model is **not** trained on OIL data.
- Multilingual phrases cover the vocabulary in `services/multilingual.py` — field reporting constantly adds new slang, so HSE review + the feedback loop keep coverage honest and growing.
- Learned signals tune confidence/evidence but never flip a verdict on their own.
- Priority scoring is an **AI-assisted prototype assessment**, not official OIL methodology.
- The SIF-potential definition, Life-Saving Rule taxonomy and workflow require HSE/OIL validation.
- AI results carry uncertainty and are **decision support** — they do not replace HSE professionals.

## Future Scope

Integration with OIL HSSE platforms · continuous ingestion · HSE-validated datasets · active learning from review feedback (full classifier re-fit) · improved SIF classification · advanced barrier/bowtie analysis · temporal trends · expanding the multilingual lexicon (more dialects/scripts) · production-scale deployment · LLM-assisted corrective-action drafting at scale.

---

*Prototype · AI-assisted · Synthetic demo data · Requires HSE/OIL validation — built for Smart India Hackathon 2026, Problem Statement 26165, Oil India Limited.*
