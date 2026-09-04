"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  FileUp,
  Loader2,
  RefreshCw,
  Table2,
  UploadCloud,
} from "lucide-react";
import type {
  FieldMapping,
  IngestJobState,
  IngestPreview,
} from "@/lib/api";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";

const ACCEPTED = ".csv,.tsv,.txt,.json,.xlsx";

const CANONICAL_LABELS: { key: keyof FieldMapping; label: string; hint: string }[] = [
  { key: "text", label: "Report text", hint: "Free text the engine analyzes (required)" },
  { key: "title", label: "Title / subject", hint: "Optional heading, joined before the text" },
  { key: "date", label: "Date", hint: "Auto-parsed across common formats" },
  { key: "site", label: "Site / location", hint: "Site_name + Location_detail merge automatically" },
  { key: "activity", label: "Activity", hint: "What was happening (maintenance, welding…)" },
  { key: "report_type", label: "Report type", hint: "Unsafe Act / Condition, Near Miss, Incident…" },
  {
    key: "report_id",
    label: "Report ID (from file)",
    hint: "Kept for display next to the generated ID — handy when several files are uploaded",
  },
  {
    key: "hazard",
    label: "Hazard",
    hint: "If the file already classifies the hazard, the file value is used as-is",
  },
  {
    key: "consequence",
    label: "Potential consequence",
    hint: "File value is used as-is when provided",
  },
  {
    key: "barrier_failure",
    label: "Barrier failure",
    hint: "Comma-separated barrier values from the file are used as-is",
  },
  {
    key: "location",
    label: "Location detail",
    hint: "File location detail is used as an intermediate analysis field",
  },
  {
    key: "equipment",
    label: "Equipment",
    hint: "Comma-separated equipment values from the file are used as-is",
  },
  {
    key: "unsafe_type",
    label: "Unsafe type",
    hint: "File classification is used as-is",
  },
  {
    key: "rule",
    label: "Life-Saving Rule",
    hint: "If the file already maps the rule, the file value is used as-is",
  },
];

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollJob(
  jobId: number,
  onState: (s: IngestJobState) => void
): Promise<IngestJobState> {
  const deadline = Date.now() + 180_000;
  for (;;) {
    const state = await api.getIngestJob(jobId);
    onState(state);
    if (state.status === "done" || state.status === "error") return state;
    if (Date.now() > deadline) {
      throw new Error("Import still running in the background — refresh this page to see its status.");
    }
    await sleep(1200);
  }
}

export default function IngestPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<IngestPreview | null>(null);
  const [overrides, setOverrides] = useState<FieldMapping>({});
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<"pick" | "preview" | "running" | "done" | "error">("pick");
  const [job, setJob] = useState<IngestJobState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourceLabel, setSourceLabel] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const mapping = useMemo<Record<string, string | null>>(() => {
    if (!preview) return {};
    const out: Record<string, string | null> = {};
    for (const c of CANONICAL_LABELS) {
      const ov = overrides[c.key];
      if (ov !== undefined) out[c.key] = ov === "" ? null : ov;
      else out[c.key] = preview.mapping[c.key] ?? null;
    }
    return out;
  }, [preview, overrides]);

  async function pickFile(f: File | null) {
    if (!f) return;
    setFile(f);
    setPreview(null);
    setJob(null);
    setOverrides({});
    setError(null);
    setPhase("pick");
    setBusy(true);
    try {
      const p = await api.ingestPreviewFile(f);
      setPreview(p);
      setPhase("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the file");
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }

  async function runImport() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setPhase("running");
    setJob(null);
    try {
      const start = await api.ingestImportFile(
        file,
        mapping,
        sourceLabel.trim() || undefined
      );
      const done = await pollJob(start.job_id, setJob);
      setJob(done);
      setPhase(done.status === "done" ? "done" : "error");
      if (done.status === "error") setError(done.error ?? "Import job failed");
    } catch (e) {
      setPhase("error");
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  function selectOption(key: keyof FieldMapping, value: string) {
    setOverrides((prev) => {
      const next = { ...prev };
      if (value === "__auto__") delete next[key]; // fall back to auto-detection
      else next[key] = value === "" ? null : value; // "" means infer from text
      return next;
    });
  }

  const total = job?.rows_total ?? preview?.total_rows ?? 0;
  const processed = job?.processed ?? 0;
  const progressPct = total > 0 ? Math.min(100, Math.round((100 * processed) / total)) : 0;

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        kicker="Dataset Ingestion"
        title="Import Any Safety-Report Dataset"
        icon={Database}
        lede={
          <>
            Upload a CSV, Excel or JSON export from any reporting system — an
            HSSE export with columns like{" "}
            <span className="font-mono text-[11px] text-ink-soft">
              Report_id, Site_name, Location_detail, Activity, Description
            </span>{" "}
            works just as well as a bespoke layout. The engine auto-detects the
            columns, runs every row through the SIF pipeline, and commits rows
            to PostgreSQL in batches — progress is shown live, and the
            dashboard updates automatically.
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {/* Step 1 — pick file */}
          <div className="card">
            <h2 className="card-title">
              <FileUp size={16} className="text-brand-600" /> 1 · Choose a dataset file
            </h2>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
            <button
              onClick={() => inputRef.current?.click()}
              className="mt-3 flex w-full flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-brand-200 bg-brand-50/40 px-6 py-10 text-center transition hover:border-brand-400 hover:bg-brand-50"
            >
              <UploadCloud size={28} className="text-brand-400" />
              <span className="text-sm font-bold text-ink">
                {file ? `Selected: ${file.name}` : "Click to choose a file"}
              </span>
              <span className="text-xs text-ink-muted">
                {ACCEPTED.split(",").join(" ")} · up to 15 MB · any column layout
              </span>
            </button>

            {busy && !preview && phase === "pick" && (
              <p className="mt-3 flex items-center gap-2 text-sm text-ink-muted">
                <Loader2 size={15} className="animate-spin text-brand-500" />
                Reading file and detecting columns…
              </p>
            )}
            {error && phase !== "running" && (
              <div className="mt-3 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
                <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
              </div>
            )}
          </div>

          {/* Step 2 — confirm mapping */}
          {preview && (phase === "preview" || phase === "running" || phase === "done") && (
            <div className="card">
              <h2 className="card-title">
                <Table2 size={16} className="text-brand-600" /> 2 · Confirm the column mapping
              </h2>
              <p className="mt-1 text-xs text-ink-muted">
                {preview.total_rows} rows found. Adjust any field — “Auto” uses smart
                detection, “None” lets the AI infer the value from the report text.
              </p>
              <div className="mt-4 space-y-3">
                {CANONICAL_LABELS.map((c) => {
                  const current = mapping[c.key];
                  return (
                    <div key={c.key} className="grid gap-2 sm:grid-cols-[150px_1fr] sm:items-center">
                      <div>
                        <label className="text-xs font-bold uppercase tracking-wider text-ink">
                          {c.label}
                        </label>
                        <p className="text-[11px] text-ink-muted">{c.hint}</p>
                      </div>
                      <select
                        disabled={phase === "running" || phase === "done"}
                        value={
                          (overrides[c.key] !== undefined
                            ? overrides[c.key]
                            : preview.mapping[c.key]) ?? "__auto__"
                        }
                        onChange={(e) => selectOption(c.key, e.target.value)}
                        className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-400 disabled:opacity-60"
                      >
                        <option value="__auto__">
                          Auto{preview.mapping[c.key] ? `: ${preview.mapping[c.key]}` : " (no match — infer from text)"}
                        </option>
                        {preview.columns.map((col) => (
                          <option key={col} value={col}>
                            {col}
                          </option>
                        ))}
                        <option value="">None — infer from text</option>
                      </select>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 2b — sample preview */}
          {preview && (phase === "preview" || phase === "running" || phase === "done") && (
            <div className="card">
              <h2 className="card-title">
                <FileSpreadsheet size={16} className="text-brand-600" /> How the first rows will be read
              </h2>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-xs">
                  <thead>
                    <tr className="border-b border-brand-100 uppercase tracking-wider text-ink-muted">
                      <th className="px-2 py-1.5">Text (analyzed)</th>
                      <th className="px-2 py-1.5">Date</th>
                      <th className="px-2 py-1.5">Site</th>
                      <th className="px-2 py-1.5">Activity</th>
                      <th className="px-2 py-1.5">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.samples.map((s, i) => (
                      <tr key={i} className="border-b border-brand-50 align-top">
                        <td className="max-w-[260px] px-2 py-2 text-ink-soft">
                          {s.text ?? <span className="italic text-ink-muted">empty — skipped</span>}
                        </td>
                        <td className="px-2 py-2 text-ink-soft">
                          {s.date ?? <span className="italic text-ink-muted">—</span>}
                        </td>
                        <td className="px-2 py-2 text-ink-soft">
                          {s.site ?? <span className="italic text-ink-muted">—</span>}
                        </td>
                        <td className="px-2 py-2 text-ink-soft">
                          {s.activity ?? <span className="italic text-ink-muted">—</span>}
                        </td>
                        <td className="px-2 py-2 text-ink-soft">
                          {s.report_type ?? <span className="italic text-ink-muted">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {phase === "preview" && (
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <input
                    value={sourceLabel}
                    onChange={(e) => setSourceLabel(e.target.value)}
                    placeholder="Source label (e.g. HSSE export Oct 2026)"
                    className="min-w-[240px] flex-1 rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
                  />
                  <button
                    onClick={runImport}
                    disabled={busy}
                    className="btn-primary justify-center disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {busy ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
                    {busy ? "Starting…" : "Analyze & Import"}
                  </button>
                  <button
                    onClick={() => {
                      setPreview(null);
                      setJob(null);
                      setFile(null);
                      setPhase("pick");
                      setError(null);
                    }}
                    className="btn-ghost"
                  >
                    Start over
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Step 3 — live progress */}
          {phase === "running" && job && (
            <div className="card">
              <h2 className="card-title">
                <RefreshCw size={16} className="animate-spin text-brand-600" /> Importing into PostgreSQL…
              </h2>
              <div className="mt-3 flex items-center justify-between text-xs font-semibold text-ink">
                <span>
                  Row {processed} of {total}
                </span>
                <span>{progressPct}%</span>
              </div>
              <div className="mt-1.5 h-3 overflow-hidden rounded-full bg-brand-100">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600 transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                <Stat label="Imported" value={job.imported} />
                <Stat label="SIF-potential" value={job.sif_potential} pink />
                <Stat label="High priority" value={job.high_priority} red />
                <Stat label="Duplicates skipped" value={job.duplicate_count ?? 0} />
                <Stat label="Failed" value={job.failed_count} />
              </div>
              <p className="mt-3 text-[11px] text-ink-muted">
                Batches are committed as they are analyzed — open the Reports or
                Dashboard page in another tab to watch rows appear before the
                import finishes.
              </p>
            </div>
          )}

          {/* Step 4 — result */}
          {phase === "done" && job && (
            <div className="card">
              <h2 className="card-title text-green-700">
                <CheckCircle2 size={16} /> Import complete — stored in the database
              </h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <StatBox label="Imported" value={`${job.imported}`} sub={`of ${job.rows_total} rows`} />
                <StatBox label="SIF-potential" value={`${job.sif_potential}`} pink sub="precursors detected" />
                <StatBox label="High priority" value={`${job.high_priority}`} red sub="require HSE review" />
                <StatBox label="Duplicates skipped" value={`${job.duplicate_count ?? 0}`} sub="identical text — not stored twice" />
                <StatBox label="Failed rows" value={`${job.failed_count}`} sub={job.skipped_empty ? `${job.skipped_empty} empty skipped` : "0 skipped"} />
              </div>

              {(job.duplicates ?? []).length > 0 && (
                <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50 p-3 text-xs text-violet-800">
                  <p className="font-bold uppercase tracking-wider text-violet-700">
                    Duplicates skipped (identical rows)
                  </p>
                  <p className="mt-1">
                    {job.duplicates!.slice(0, 5).map((d) => (
                      <span key={d.row} className="mr-3 inline-block">
                        Row {d.row} → duplicate of {d.duplicate_of}
                      </span>
                    ))}
                    {(job.duplicates?.length ?? 0) > 5 && (
                      <span>… and {(job.duplicates?.length ?? 0) - 5} more</span>
                    )}
                  </p>
                </div>
              )}

              {job.failures.length > 0 && (
                <div className="mt-3 max-h-40 overflow-y-auto rounded-xl border border-amber-300 bg-white p-3">
                  {job.failures.map((f) => (
                    <p key={f.row} className="text-xs text-amber-800">
                      Row {f.row}: {f.error}
                    </p>
                  ))}
                </div>
              )}

              <div className="mt-4 flex flex-wrap gap-3">
                <Link href="/reports" className="btn-primary">
                  View imported reports <ArrowRight size={15} />
                </Link>
                <Link href="/" className="btn-ghost">
                  Dashboard — analytics updated
                </Link>
              </div>
              <p className="mt-3 text-[11px] text-ink-muted">{job.note}</p>
            </div>
          )}
        </div>

        {/* Side panel */}
        <div className="space-y-4">
          <div className="card">
            <h2 className="card-title">
              <RefreshCw size={16} className="text-brand-600" /> The real flow
            </h2>
            <ol className="mt-3 space-y-2.5 text-sm text-ink-soft">
              {[
                "Any file: CSV, Excel, JSON — any column names",
                "Auto map text / date / site / activity columns",
                "Store raw rows in PostgreSQL with a processing status",
                "Skip identical duplicates automatically (never stored twice)",
                "Classify each row: SIF potential + Life-Saving Rule + priority",
                "Progress & partial results commit in batches (live updates)",
                "Dashboard, barriers and patterns update automatically",
                "HSE reviews every AI result (human-in-the-loop)",
              ].map((step, i) => (
                <li key={step} className="flex gap-2.5">
                  <span className="grid h-5 w-5 flex-shrink-0 place-items-center rounded-full bg-brand-100 text-[11px] font-bold text-brand-700">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          <div className="card">
            <h2 className="card-title">
              <FileUp size={16} className="text-brand-600" /> No renames needed
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              Any column layout works. Names like “Date of Incident”, “Location”
              and “Description” are auto-detected, and HSSE exports
              (Report_id, Site_name, Location_detail, Description, …) map
              directly to the pipeline.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, pink, red }: { label: string; value: number; pink?: boolean; red?: boolean }) {
  return (
    <div className="rounded-xl bg-brand-50/60 p-2.5">
      <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">{label}</p>
      <p className={`text-xl font-extrabold ${pink ? "text-brand-600" : red ? "text-red-600" : "text-ink"}`}>
        {value}
      </p>
    </div>
  );
}

function StatBox({ label, value, sub, pink, red }: { label: string; value: string; sub: string; pink?: boolean; red?: boolean }) {
  return (
    <div className="rounded-xl bg-brand-50/60 p-3">
      <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">{label}</p>
      <p className={`text-2xl font-extrabold ${pink ? "text-brand-600" : red ? "text-red-600" : "text-ink"}`}>{value}</p>
      <p className="text-[11px] text-ink-muted">{sub}</p>
    </div>
  );
}


