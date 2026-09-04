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

## Our Solution

An **AI Safety Early-Warning & SIF Precursor Intelligence Platform** that:

1. Ingests free-text safety reports (UA / UC / near-miss / incident).
2. Detects potential SIF precursors with a **hybrid, explainable NLP pipeline**.
3. Shows **evidence** — the exact phrases that triggered the flag.
4. Extracts hazard, potential consequence, barrier failure, activity, equipment.
5. Maps reports to the relevant **Life-Saving Rule** — the canonical ten: Work Authorization, Energy Isolation, Bypassing Safety Controls, Confined Space Entry, Working at Height, Safe Mechanical Lifting, Toxic Gas Safety, Driving Safety, Line of Fire, Hot Work Safety.
6. Assigns a transparent **AI-assisted priority** (HIGH / MEDIUM / LOW) — prototype methodology.
7. Surfaces **recurring patterns** (e.g. repeated energy-isolation failures during maintenance) — never fabricated.
8. Links **similar historical reports** — every stored report, dashboard row and fresh analysis shows its closest past matches with click-through.
9. Provides an **HSE dashboard** and a **human-in-the-loop review + retraining workflow** where HSE experts confirm, reject or correct AI results and re-train the decision signals on those labels.
10. **Dedicated HSE Reviewer workspace** (`/review`) — a separate inbox from the general Reports registry so reviewers are never lost among search/export/admin controls. It shows exactly what still needs a human decision (with a live pending-count badge in the nav), lets the reviewer **Verify as SIF / Not SIF** in one click, and lists verified and rejected records with clear, distinct badges ("Needs HSE review" vs "HSE verified" vs "Rejected · not SIF").
11. **Missing-field intelligence made visible** — every report page shows a *Field Coverage* panel: each field is tagged **Source file** (authoritative when the file provides it), **AI text analysis** (filled by the engine when the file is silent) or **Not stated** (never fabricated). File-provided values are authoritative and used as-is; the engine only fills fields the file leaves blank.
12. **Duplicate indication** — rows whose report text is stored more than once get a *Possible duplicate* badge in the Reports table (with a dedicated queue filter), and the report page flags semantic near-copies (closest match ≥ 88% similar) with a direct link to compare — so the same incident re-reported or a file imported twice is never analyzed twice silently.
13. **Duplicate-safe imports** — when a dataset is imported, rows whose text already exists in the database (or is repeated inside the same file) are skipped automatically and reported as *duplicates skipped* on the import result — identical rows are never stored twice.
14. **Similar solved case → reference (site A → site B)** — every similar report now carries its site and HSE review state. When the current report matches a case another site already verified (ideally with action notes), the report page highlights it as the reference and asks HSE to check whether the same corrective action applies.
15. **Recurring pattern intelligence** — pattern cards are backed by the real member reports: click a pattern to open them in the registry (each report opens with its own similar history), and a *How patterns are found* popup documents the mapping criteria (rule+activity, rule+barrier, hazard+activity on ≥ 2 SIF-potential reports). Barrier cards link straight to the real report set instead of inline examples.
16. **Field-derived estimation** — when a dataset omits the Life-Saving Rule (and the text gives no signal), the engine estimates it from the file's structured hazard/activity values and says so in the uncertainty note — the field is never left blank when derivable.
- **App shell** — navigation lives in a fixed **left sidebar** on desktop (Work: Dashboard · HSE Review · Reports · Analyze · Import Data — Insights: Life-Saving Rules · Recurring Patterns · Site Risk · Activities · Barrier Failures · Model Evaluation), with a drawer on mobile. The SIF trend chart adds a **Bar + line** composed view, and non-English reports show a language chip (Hindi / Bengali / Assamese, native or romanised).

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
| **Multilingual layer** | Understands Hindi, Bengali and Assamese safety reports — Devanagari/Bengali script and romanised Hinglish/Benglish — mapping the same explicit failure phrases to the same Life-Saving Rules and quoting the original text as evidence. |
| **NLP / ML** | Structured extraction (activity, hazard, barrier, equipment, unsafe act/condition). Traditional ML slots in here when labeled OIL data becomes available. |
| **Narrative** | Deterministic plain-language summary (“what happened / why it matters / next step”) + rule-based corrective-action checklist from the structured result. |
| **Similarity** | Similar-report linking from text overlap + shared rule / hazard / barrier / activity — no external model required, works across languages. |
| **LLM (Llama via Groq, optional)** | Complex interpretation, explanation polish, summary rephrase and follow-up suggestions — **Pydantic-validated, with graceful fallback** to the deterministic result when unavailable or invalid. |
| **Feedback → retraining** | Every HSE review is stored as a labeled example; *Train on reviewed labels* measures model↔human agreement and learns signals from the disagreements, which tune future analyses. |
| **Human** | HSE professionals make the final call through the review workflow. |

## Algorithms Used

Everything below runs offline, is deterministic and explainable — the optional LLM only polishes output.

| # | Algorithm / method | What it does | Where it lives |
|---|---|---|---|
| 1 | **Negation-aware rule matching** | Keyword + phrase patterns per Life-Saving Rule, matched with negation detection (“without isolation”, “no permit”, “missing guard”) so a control that is *present* is not flagged as breached. Quotes the exact evidence phrase. | `safety_lexicon.py`, `sif_detector.py` |
| 2 | **Additive priority scoring** | `score = min(matched_indicators, 3) + severity_bonus(0–2) + people_exposure(0–1) + barrier_failure(0–1)`; HIGH ≥ 5, MEDIUM ≥ 3, else LOW. Confidence = `0.62 + 0.11·indicators + 0.05·severity`, capped at 0.97. The four factors are stored per report and shown as a “how it was calculated” breakdown. | `risk_scorer.py` |
| 3 | **Life-Saving-Rule classification** | Per-condition mapping of the text to each rule's requirements with a `breached / in_place / not_verifiable` verdict and per-condition evidence. | `rules` engine + `rule_conditions` |
| 4 | **Rule estimation from structured fields** | When the file/text gives no Life-Saving Rule signal, the rule is estimated from the file's own hazard/activity values (e.g. hazard “confined space entry” → Confined Space Entry) and the derivation is stated in the uncertainty note. | `ingest.py` (`estimate_rule_from_fields`) |
| 5 | **Language detection (multilingual)** | Script detection for Devanagari / Bengali / Assamese plus romanised Hinglish / Benglish lexicons; the same failure phrases map to the same rules across languages. | `languages` in the analysis pipeline |
| 6 | **Hybrid similarity linking** | Similar-report score from token overlap (normalised word-level similarity) **plus** shared rule / hazard / barrier / activity concept bonuses (capped low so genuine near-copies outscore distinct-but-related precursors). Scores are shown with the shared fields on the report page. | `similarity.py` |
| 7 | **Duplicate detection** | Import-time text fingerprinting skips identical rows (reported as “Row N → duplicate of RPT-x”) and near-copies (similarity ≥ 0.88) are flagged as `duplicate_of` on the report detail. | `ingest.py`, `reports.py` (`DUP_SIMILARITY = 0.88`) |
| 8 | **Feedback → retraining loop** | Every HSE review is stored as a labelled example; “Train on reviewed labels” computes model↔human agreement (precision / recall / F1), mines the surface phrases of disagreements, and applies them as weighted learned signals to future analyses. | `adaptive.py` |
| 9 | **Honest field inference** | Each field is tagged *Source file* (authoritative), *AI text analysis* (inferred), or *Not stated* — the engine never fabricates values; file-provided values are used as-is and the AI extraction is kept for reference. | `ingest.py`, `analysis_pipeline.py` |
| 10 | **Recurring-pattern mining** | Co-occurrence grouping of ≥ 2 SIF-potential reports by rule+activity / rule+barrier / hazard+activity, backed by the real member reports and clickable into the filtered registry. | `analytics.py` (`/patterns`) |
| 11 | **Trend & density analytics** | Weekly trend bucketing; SIF precursor density = SIF-potential ÷ total reports; week-over-week deltas; chart types area / line / bar / bar+line on the same data. | `analytics.py`, dashboard |
| 12 | **Evaluation harness + stability CV** | Holdout golden set (35 hand-labelled reports across EN/HI/BN/AS) with per-class and per-rule precision / recall / F1, plus a stratified k-fold stability check (mean ± std and 95% CI over folds stratified by SIF label × language). | `evaluation.py` (`run_evaluation`, `run_kfold_cv`) · page + CLI |
| 13 | **LLM refinement (optional)** | Llama (Groq) rephrases explanations / summaries / follow-ups with Pydantic-validated output and deterministic fallback when unavailable. | `llm.py` |

## Features

- **SIF-potential detection** with evidence, hazard, potential consequence, barrier failure, Life-Saving Rule, confidence and a grounded explanation.
- **Honest information extraction** — values are `Not specified` when not stated; `explicit` vs `AI-inferred` is distinguished where relevant; nothing is invented.
- **Report analysis UI** — paste any report, get an explainable structured result.
- **Generic dataset ingestion** — upload CSV / Excel / JSON with any column names; the engine auto-maps columns, runs every row through the pipeline, stores results (PostgreSQL or SQLite) and the dashboards update automatically.
- **HSE Dashboard** — KPIs, SIF trend, Life-Saving Rule distribution, recent high-priority reports.
- **Analytics pages** — Life-Saving Rules, Site Risk, Activities, Barrier Failures, Recurring Patterns. Metrics are labeled honestly (raw counts vs density) and never fabricated.
- **HSE human review** — a dedicated **Review Queue** page (nav badge shows pending count) plus the per-report panel: confirm / reject SIF, change priority or rule, edit comments, mark reviewed; feedback is stored for future model improvement. Badges are unambiguous: **Needs HSE review · HSE verified · HSE reviewed · HSE edited · Rejected · not SIF**.
- **Reports registry** — search now spans the narrative plus IDs, site, activity, report type, Life-Saving Rule and hazard; filters cover report type/category, source file, review status and possible duplicates; the queue chips distinguish pending from HSE-verified from rejected.
- **Multi-language detection** — Hindi, Assamese and Bengali reports (native script and romanised) are analyzed and mapped to the same rules, with the detected languages shown on the result. *A big differentiator for OIL's real, code-mixed reports.*
- **Plain-language summary + suggested actions** — every analysis includes a three-part human-readable summary (“what happened / why it matters / next step”) and a concrete corrective-action checklist generated from the rule profile and failed barriers.
- **Similar past reports** — deterministic semantic linking (text overlap + shared rule/hazard/barrier/activity) surfaces “N similar” on the dashboard, on the report detail page and right after an ad-hoc analysis, each clickable.
- **Feedback → retraining loop** — HSE review decisions are stored as labeled examples (`feedback` table); the *Train on reviewed labels* button recomputes model↔human agreement (precision/recall/F1), mines learned signal phrases from the disagreements and applies them (marked `rules-v1+tuned`) to future analyses.
- **Evaluation harness** — a hand-labeled golden set of 35 reports (English + Hindi + Bengali + Assamese) with a live **Evaluation** page and CLI showing SIF classification and per-Life-Saving-Rule precision / recall / F1 — no fabricated numbers.
- **Light & dark themes** — an OIL-appropriate design system: deep navy primary, charcoal ink, light-gray canvas, with red/orange (danger), amber (warning), green (validated) and violet (AI accent) keeping their meanings. The header moon/sun toggle remembers your choice; the first visit follows the OS preference. Charts, tooltips and every view re-tint live without a reload.
- **Graceful degradation** — no LLM key, no embeddings model, no database? The API still runs on deterministic rules with a local SQLite fallback.

## Technology Stack

**Frontend:** Next.js (App Router) · React · Tailwind CSS · Recharts · Lucide React

**Backend:** Python · FastAPI · Pydantic v2 · SQLAlchemy

**AI/NLP:** Rule-based NLP + multilingual lexicons (primary) · Llama via Groq (optional) · scikit-learn / Sentence Transformers (optional, when labeled data/keys available)

**Database:** Local PostgreSQL or SQLite fallback
<<<<<<< HEAD
**Docs:** `docs/index.html` project showcase · `docs/processing.html` data-processing stages and the algorithm behind every output field
=======

**Docs:** standalone `docs/index.html` showcase · `docs/MANUAL_TESTING.md` step-by-step QA checklist
>>>>>>> 45f8118d6c50a12fdba1e11818f497847069b30b

## Repository Structure

```
SIH-SIF-Precursor-Detection/
├── frontend/                  # Next.js application
│   ├── app/                   # pages: /, /review (HSE queue), /analyze, /ingest,
│   │                          #   /reports, /reports/[id], /rules, /sites,
│   │                          #   /activities, /barriers, /patterns, /evaluation
│   ├── components/            # nav (with dark/light toggle), footer, badges,
│   │                          #   analysis-result card, rules-guide popup, theme provider
│   └── lib/                   # typed API client, theme-aware chart palette
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint (lifespan seeds demo data)
│   │   ├── config.py          # settings from env
│   │   ├── api/               # reports, ingest, review, analytics, feedback, evaluation routers
│   │   ├── services/          # sif_detector, rule_classifier, information_extractor,
│   │   │                      # risk_scorer, analysis_pipeline, ingest, llm,
│   │   │                      # safety_lexicon, multilingual, narrative, similarity,
│   │   │                      # adaptive (feedback->retrain), evaluation (golden-set metrics)
│   │   ├── models/            # SQLAlchemy entities + engine/session (reports, analyses,
│   │   │                      #   reviews, feedback, training_runs, life_saving_rules…)
│   │   ├── schemas/           # Pydantic schemas
│   │   └── data/              # life_saving_rules, demo dataset, golden evaluation set
│   ├── scripts/               # engine verification + API smoke/ingest tests
│   ├── requirements.txt
│   └── README.md
├── docs/
│   └── index.html             # polished standalone documentation site
├── docker-compose.yml         # local PostgreSQL for the real database flow
├── .env.example
├── .gitignore
└── README.md
```

## Setup

### Prerequisites
- Python 3.11+ and Node.js 18+

### Quick start (three terminals)

```bash
# terminal 1 — real database flow (optional: default is a zero-setup SQLite file)
#   docker compose up -d   # + DATABASE_URL in backend/.env -> see "Using PostgreSQL"

# terminal 2 — backend API  ->  http://127.0.0.1:8000/docs
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 3 — web app  ->  http://127.0.0.1:3000
cd ../frontend
npm install
npm run dev
```

Then open http://127.0.0.1:3000, go to **Import Data** and upload your own CSV / Excel / JSON (or paste JSON rows). Each row is stored, analysed by the AI engine and shown on the dashboard automatically. Full per-component instructions follow.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # optional — sensible defaults exist
uvicorn app.main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health
- On first start the backend **creates tables automatically** and, unless disabled, seeds 45 clearly-labeled synthetic demo reports so the dashboard is not empty. Set `SEED_DEMO_DATA=0` (e.g. `backend/.env`) to keep the database empty and verify with your own imported data.
- **Data you import is saved in PostgreSQL and survives backend restarts** — nothing is cleared or re-seeded at startup when seeding is disabled (the log line `Demo seeding disabled — database stays empty for real data` confirms it).

#### Using PostgreSQL (the real database flow)

The default `DATABASE_URL` is a local SQLite file so the demo runs with zero setup. To use **PostgreSQL**:

```bash
docker compose up -d                       # starts sif-postgres on :5432 (repo root)
pip install "psycopg[binary]" openpyxl     # PostgreSQL driver + XLSX ingestion
# .env:  DATABASE_URL=postgresql+psycopg://sif:sif@localhost:5432/sif_detection
uvicorn app.main:app --reload --port 8000  # creates schema + seeds demo data in Postgres
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:3000
```

The frontend reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

> Appearance: use the **moon / sun button** in the header to switch between dark and light mode. The choice is remembered in the browser; the first visit follows the operating-system preference.

### 3. Viewing the demo

```bash
# Documentation — just open in a browser:
open docs/index.html             # project showcase
open docs/processing.html        # how data is processed + per-field algorithms
```

## Environment Variables (`.env.example`)

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | No | Optional LLM refinement (Llama via Groq). Without it, rule-based analysis runs. |
| `SEED_DEMO_DATA` | No | `1` (default) seeds 45 synthetic demo reports when the DB is empty; `0` keeps it empty for real imports. |
| `DATABASE_URL` | No | PostgreSQL URL for the local Docker database. Defaults to local SQLite (`sqlite:///./sif_detection.db`) when unset. |
| `NEXT_PUBLIC_API_URL` | No | Frontend → backend base URL. |

Never commit real credentials. Never commit a `.env` file.

## Ingesting Your Own Dataset (any format)

The platform is **dataset-agnostic** — it analyzes any safety-report dataset, not just the synthetic demo. The full flow is:

```
Dataset file (CSV / Excel / JSON, any columns)
        ↓  auto-detect column mapping
Preview: which column is the report text / date / site / activity?
        ↓  (adjust mapping if needed)
Each row → mapped to report fields → SIF pipeline (detect → evidence →
         hazard → barrier → rule → priority)
        ↓
PostgreSQL: report + analysis stored (source label kept)
        ↓
Dashboard, sites, activities, barriers & patterns update automatically
        ↓
HSE review of any flagged report
```

Try it in the UI: **Import Data** page (top nav) or directly via the API:

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

Column synonyms are auto-detected (e.g. *Report / Description / Narrative / Observation / What happened* → text; *Site / Location / Plant / Area / Work location* → site; *Date of occurrence / Reported on* → date; *Activity / Nature of work / Type of job* → activity; *Type / Category* → report type). Dates are parsed across common formats. Rows with no explicit metadata are still fully analyzed from free text — nothing requires the demo schema.

`backend/scripts/verify_ingest.py` runs the whole flow against a deliberately foreign-format CSV.

## Demo Data

All demo reports in `backend/app/data/demo_reports.py` are **synthetic, invented scenarios** labeled `Demo / Synthetic Data` in the UI. They cover Energy Isolation, Confined Space, Hot Work, Working at Height, Line of Fire, Lifting, Driving, Electrical and Bypassing Safety Controls — with deliberately recurring patterns (e.g. energy-isolation failures during maintenance, missing gas testing before confined-space entry) so the analytics and pattern pages have meaningful data to show.

## API Overview

```
GET    /api/health
POST   /api/reports/analyze        # analyze (store=true/false)
POST   /api/reports                # create + analyze + store
GET    /api/reports                # list (filters: site, activity, priority, rule, status, sif, q)
GET    /api/reports/counts         # quick counts: total / pending / verified / rejected / failed
GET    /api/reports/{id}           # full detail incl. analysis + review + possible duplicate
POST   /api/reports/{id}/reanalyze # re-run pipeline, update stored analysis
PATCH  /api/reports/{id}/review    # HSE review decision
POST   /api/ingest/file/preview    # upload dataset, preview mapping (no writes)
POST   /api/ingest/file            # start import job for an uploaded file
POST   /api/ingest/rows            # start import job for raw JSON rows
GET    /api/ingest/jobs/{id}       # poll job progress (persisted in the DB)
GET    /api/ingest/jobs            # recent import jobs
GET    /api/analytics/overview     # KPIs + trend + recent high-priority
GET    /api/analytics/life-saving-rules
GET    /api/analytics/sites
GET    /api/analytics/activities
GET    /api/analytics/barriers
GET    /api/analytics/patterns
GET    /api/evaluation          # golden-set SIF + per-Life-Saving-Rule metrics
GET    /api/feedback/summary    # reviewed-label counts + latest training run
POST   /api/feedback/train      # train on reviewed labels (metrics + learned signals)
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

Also handles Devanagari (`गैस टेस्ट के बिना`), Bengali (`গ্যাস টেস্ট করা হয়নি`, roman “gas test chara”) and Assamese (`গেছ টেষ্ট নকৰাকৈ`) phrases — try the Hindi / Bengali example chips on the Analyze page.

## Evaluation

The platform ships two distinct, complementary evaluation benchmarks on the **Model Evaluation** (`/evaluation`) page:

### 1. Deterministic Golden-Set Engine Benchmark (35 Multi-lingual Cases)
- **What it is**: A hand-labeled reference set of 35 incident reports in `backend/app/data/golden_set.py` covering all ten Life-Saving Rules across English, Hindi (Devanagari & Hinglish), Bengali, and Assamese.
- **Purpose**: Tests the **Rule-Based & Multi-Lingual Engine** (deterministic, offline). It verifies that regional phrase patterns and script translations correctly fire specific Life-Saving Rules and detect SIF potential without needing an external LLM.

### 2. Stratified 5-Fold ML Cross-Validation (500 SIF Reports Dataset)
- **What it is**: A 5-fold cross-validation suite over a 500-report SIF dataset (`backend/app/data/oil_hsse_sif_dataset.csv`).
- **Purpose**: Evaluates **Statistical Machine Learning Models** (Multinomial Naive Bayes, Logistic Regression, Linear SVM) against a Rule Engine Baseline. It isolates TF-IDF vectorization within each fold to prevent data leakage and measures per-fold Precision, Recall, $F_1$, and safety-critical $F_2$ scores.

> **Key Distinction**: The Golden Set (35 cases) evaluates **rule-based multi-lingual coverage**, while the 5-Fold Cross-Validation (500 reports) evaluates **statistical ML algorithm performance**.

```bash
cd backend
python scripts/evaluate.py --cv 5   # compact + k-fold stability table
python scripts/evaluate.py --json --cv 5
```

- `backend/scripts/verify_engine.py` runs detection-agreement checks on the synthetic demo set; `backend/scripts/verify_ingest.py` exercises the generic-dataset ingestion flow.
- **Human agreement** — reviewed reports become labeled examples; `POST /api/feedback/train` (or the *Train on reviewed labels* button on the Reports page) recomputes AI↔HSE agreement and mined signals. The same k-fold seams become train/test splits for the adaptive signals once enough reviewed feedback accumulates.
- Recall matters most: missing a genuine SIF precursor is more serious than an extra false alert. **No claim of accuracy on real OIL data is made** — metrics describe the deterministic rules on the in-repo reference set and require HSE-validated labels to generalize.

### Validating with real data (TSTR roadmap)

The golden set was authored against the same rule lexicon, so perfect scores there prove *consistency*, not *real-world generalization*. The planned external validation ladder (documented here so reviewers see the intent):

1. **TSTR (Train-Synthetic-Test-Real)** — generate synthetic rows from a train split only, train, and evaluate on a *real* holdout (e.g. a manually labeled slice of OSHA / MSHA / Canada-OHS incident text). Synthetic-trained F1 within ~90–95% of real-trained F1 ⇒ the synthetic data has utility.
2. **Statistical fidelity** — Kolmogorov–Smirnov over numeric fields (exposure/risk scores), chi-square / total-variation distance over categorical fields (rule, activity, barrier), correlation-matrix and Jensen–Shannon comparisons over feature pairs between synthetic and real sets.
3. **Discriminator test** — train a simple classifier on the real-vs-synthetic task; accuracy near 50% means the synthetic distribution is hard to distinguish; well above chance points to which features to re-generate.
4. **Near-duplicate audit** — cosine similarity on embeddings plus rule+activity+barrier tuple frequencies, to ensure generation adds diversity rather than near-copies.
5. **Human expert review** — HSE scores a sample of synthetic reports for plausibility and correct rule mapping (extends the existing feedback loop to generation).

## Limitations

- Demo data is synthetic; the model is **not** trained on OIL data.
- Multilingual phrases cover the vocabulary in `services/multilingual.py` — field reporting constantly adds new slang, so HSE review + the feedback loop keep coverage honest and growing.
- Learned signals tune confidence/evidence but never flip a verdict on their own.
- Priority scoring is an **AI-assisted prototype assessment**, not official OIL methodology.
- The SIF-potential definition, Life-Saving Rule taxonomy and workflow require HSE/OIL validation.
- AI results carry uncertainty and are **decision support** — they do not replace HSE professionals.

## Future Scope

Integration with OIL HSSE platforms · continuous ingestion · HSE-validated datasets · active learning from review feedback (full classifier re-fit) · improved SIF classification · advanced barrier/bowtie analysis · temporal trends · expanding the multilingual lexicon (more dialects/scripts) · production-scale deployment · LLM-assisted corrective-action drafting at scale.

---

*Prototype · AI-assisted · Synthetic demo data · Requires HSE/OIL validation — built for Smart India Hackathon 2026, Problem Statement 26165, Oil India Limited.*
