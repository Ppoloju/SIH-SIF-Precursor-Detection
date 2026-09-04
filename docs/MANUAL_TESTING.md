# Manual Testing Guide — SIF Precursor Detection

Run the app as a **real user** with your own data. The database ships empty;
nothing is pre-seeded. Use this checklist top-to-bottom — each row tells you
what to do and the result you should see. ~25 minutes.

---

## 0 · Preconditions & reset

- [ ] **Services up**
  - Frontend: `http://127.0.0.1:3000` (Next.js dev server)
  - Backend API: `http://127.0.0.1:8000` — docs at `/docs`
  - PostgreSQL: `sif-postgres` on `:5432` (`docker compose up -d`)
- [ ] **Database empty** — dashboard shows “Your database is empty” with
      Import / Analyze CTAs, the nav pill says “Live · 0 reports”.
- [ ] **Reset whenever you want a clean slate** (from repo root):
      ```bash
      cd backend
      # 1) stop the API, 2) empty every table, 3) start the API again:
      # (the running instance reads backend/.env → SEED_DEMO_DATA=0, so it stays empty)
      ```
  - Want the 45 labeled demo reports back for a judge run?
    `SEED_DEMO_DATA=1 python -m uvicorn app.main:app --port 8000` (or set it in `backend/.env`).

---

## 1 · Empty-state & basics

- [ ] **Dashboard empty state** — `/` shows zeroed KPIs, no charts, and clear
      “get started” actions instead of empty chart boxes.
- [ ] **Navigation** — desktop links and the mobile hamburger drawer both reach all 11
      pages; current page is highlighted; the drawer closes on navigation.
- [ ] **“What are these rules?” popup** — Rules page header + dashboard “view
      rules” link open the modal with all **10 canonical Life-Saving Rules**;       X / backdrop / Escape all close it.
- [ ] **Evaluation page** (`/evaluation`) — runs even with an empty database:
      shows golden-set metrics (35 cases, all ten rules, 7 language groups),
      per-rule F1 bars, and a working “Re-run evaluation”.

## 2 · Import real data (the main flow)

- [ ] **JSON paste (fastest)** — open **Import Data**, paste on the right:

      ```json
      [
        {"What happened": "Technician started maintenance on a live pipeline without isolating the energy source.", "Location": "Site A - Pump house", "Type": "Near Miss"},
        {"What happened": "Two workers entered the storage tank without gas testing and no attendant was posted.", "Location": "Site B", "Activity": "Tank cleaning"},
        {"What happened": "Contractor ne bina gas test ke tank ke andar kaam shuru kar diya aur koi attendant nahi tha.", "Location": "Site A", "Type": "Near Miss"},
        {"What happened": "Crane lifted the load beyond rated capacity with no banksman; worker stood under the load.", "Location": "Site B", "Activity": "Lifting"},
        {"What happened": "Welding was done near fuel drums without a hot work permit and no fire watch.", "Location": "Site A"},
        {"What happened": "Driver sped inside the yard and reversed without a spotter near the loading bay.", "Location": "Site C", "Type": "Incident"},
        {"What happened": "All crew wore harnesses with proper anchorage; gas tests done before entry — results normal.", "Location": "Site B"}
      ]
      ```
- [ ] **Auto-mapping preview** — a “What happened” column should map to the
      report text, “Location” → site, “Type” → report type, Activity detected
      automatically.
- [ ] **Live progress** — after Import, a job progress bar runs in the UI and
      counts tick up **from the database** (poll `/api/ingest/jobs/{id}`).
- [ ] **Results land** — 7 rows imported: rows 1–6 should be **SIF-potential**
      (row 3 flagged via Hindi phrases), row 7 **Non-SIF** (controlled work —
      never a false alarm).

- [ ] **CSV / Excel import** — same page: upload any `.csv`/`.xlsx` export;
      check the auto-detected column map in preview, import, and confirm rows
      appear on the Reports page with `Imported · filename` provenance.
- [ ] **Mapping override** — re-import with an explicit mapping (e.g. set text
      to a column named `Narrative`) and confirm only the chosen columns are used.

## 3 · Analysis & detail page

- [ ] **Analyze page** — paste a report; click each example chip, including       **Hindi** and **Bengali** example chips; run; stored result links to the report.
- [ ] **Detail page** — shows: original text, verdict + confidence + priority,
      **Languages chips**, “In plain language” (What happened / Why it matters /
      Next step), evidence quoted verbatim from the original report, hazard /
      barrier / rule, and a **Suggested corrective actions** checklist.
- [ ] **Similar reports** — with ≥2 similar rows in the DB, the detail page
      lists “N similar historical reports”; clicking a row opens that report.
- [ ] **Dashboard linkage** — the dashboard’s Recent High-Priority table shows a
      **“N similar”** badge per row linking to the report page.

## 4 · HSE review + retraining loop (human-in-the-loop)

- [ ] Open a SIF report → **Confirm SIF** (+ comment) → status becomes
      *Confirmed*; the HSE Review Record card appears.
- [ ] Open a report you disagree with → **Reject SIF** (or edit priority/rule)
      → status *Rejected/Edited*.
- [ ] **Reports page** — the violet pill now reads “Train on N reviewed labels”.
      Click it → shows a training-run banner: labels count, **AI ↔ HSE
      agreement %, precision / recall / F1**, and any *learned signal phrases*.
- [ ] **Signals applied** — after training, re-analyze a report containing a
      learned phrase (“Re-run AI analysis”): model tag becomes `rules-v1+tuned`,       a **Review flag** explains the learned pattern, and confidence is
      nudged — the verdict never auto-flips.

## 5 · Analytics & dashboards (after import)

- [ ] **Dashboard** — KPIs (reports / SIF / SIF density donut / high priority),
      trend with week-over-week deltas, rule distribution, focus insights.
- [ ] **Rules / Sites / Activities / Barriers / Patterns** pages — populated,
      consistent with Reports; Patterns only shows combinations with ≥2 rows.
- [ ] **Reports filters** — chips (All / SIF / High / Pending) and every
      dropdown filter + free-text search narrow correctly; “Clear filters”
      restores the full list; `?priority=HIGH` deep-link pre-filters.
- [ ] **Export CSV** — present on every data view; downloads a date-stamped
      file that opens cleanly in Excel (UTF-8 BOM, quoted cells); Reports
      exports the *currently filtered* view.
- [ ] **Freshness** — “Data updated as of … IST” reflects new imports; the
      dashboard refreshes itself while visible (~20 s) and on tab focus.

## 6 · Hardening / negative tests

- [ ] **No false alarms** — import a “routine, controlled” report; it must stay
      **Non-SIF / LOW** (try: *“Isolation applied, gas test done, harness worn,
      permit valid — work completed safely.”*).
- [ ] **Missing/empty rows** — a CSV row with no text is skipped, reported as
      `skipped_empty`, and never crashes the job.
- [ ] **Malformed dates / missing metadata** — rows still import; the engine
      infers from text where possible and shows “Not specified” otherwise.
- [ ] **Re-analysis** — changing a stored report isn’t possible (read-only), but
      “Re-run AI analysis” refreshes the stored result and resets review state
      (prior reviews are removed as superseded).
- [ ] **Graceful offline** — without `GROQ_API_KEY` nothing breaks: analysis is
      deterministic, `llm_refined` stays false, and responses stay fast.
- [ ] **Console/API health** — DevTools console has no errors during a full
      pass; `GET /api/health` returns 200.

## 7 · API smoke (optional, for the curious)

```bash
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/reports/analyze -H "Content-Type: application/json" \
  -d '{"report_text":"Worker entered the vessel without gas testing and no attendant was posted.","store":false}'
curl http://127.0.0.1:8000/api/feedback/summary
curl http://127.0.0.1:8000/api/evaluation
curl -X POST http://127.0.0.1:8000/api/feedback/train
python scripts/evaluate.py   # from backend/
```

---

*Expectation notes: verdicts are rules-based and conservative — a “HIGH / SIF”
flag requires real indicator + failure language in the text. If a test case
behaves differently than expected, capture the report text + the evidence list
shown — that combination explains exactly why.*
