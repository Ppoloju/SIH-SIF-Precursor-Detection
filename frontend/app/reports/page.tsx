"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  BrainCircuit,
  Eye,
  FileText,
  GraduationCap,
  Loader2,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import type { FeedbackSummary, ReportDetail, TrainResponse } from "@/lib/api";
import { api } from "@/lib/api";
import { PriorityBadge, ReviewBadge, SifBadge } from "@/components/Badges";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

const PRIORITIES = ["", "HIGH", "MEDIUM", "LOW"];
const STATUSES = ["", "pending", "confirmed", "rejected", "edited", "reviewed"];

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [site, setSite] = useState("");
  const [activity, setActivity] = useState("");
  const [priority, setPriority] = useState("");
  const [rule, setRule] = useState("");
  const [status, setStatus] = useState("");
  const [sif, setSif] = useState("");
  const [file, setFile] = useState("");

  // Human-in-the-loop: reviewed labels + "train" action.
  const [fb, setFb] = useState<FeedbackSummary | null>(null);
  const [trainBusy, setTrainBusy] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResponse | null>(null);

  useEffect(() => {
    // Support ?priority=HIGH (deep links from the dashboard review queue).
    const params = new URLSearchParams(window.location.search);
    if (params.get("priority") === "HIGH") setPriority("HIGH");
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await api.getReports({ limit: "10000" });
        if (cancelled) return;
        setReports(data);
        setError(null);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    api
      .getFeedbackSummary()
      .then(setFb)
      .catch(() => {});
    // Refresh when the user returns to the tab so imported rows appear.
    const onVisible = () => {
      if (document.visibilityState === "visible") load();
    };
    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  const rules = useMemo(() => {
    const set = new Set<string>();
    reports.forEach((r) => r.analysis?.life_saving_rule && set.add(r.analysis.life_saving_rule));
    return Array.from(set).sort();
  }, [reports]);

  const filtered = useMemo(() => {
    return reports.filter((r) => {
      if (q && !r.report_text.toLowerCase().includes(q.toLowerCase())) return false;
      if (site && r.site !== site) return false;
      if (activity && (r.analysis?.activity ?? r.activity) !== activity) return false;
      if (priority && r.analysis?.priority !== priority) return false;
      if (rule && r.analysis?.life_saving_rule !== rule) return false;
      if (status && r.review_status !== status) return false;
      if (file && r.source !== file) return false;
      if (sif === "true" && !r.analysis?.sif_potential) return false;
      if (sif === "false" && r.analysis?.sif_potential) return false;
      return true;
    });
  }, [reports, q, site, activity, priority, rule, status, sif, file]);

  const files = useMemo(
    () =>
      Array.from(
        new Map(
          reports
            .filter((r) => r.source)
            .map((r) => [r.source, r.source as string])
        ).values()
      ).sort((a, b) => a.localeCompare(b)),
    [reports]
  );
  // Display name for a report source ("upload:filename.csv" -> filename).
  const prettySource = (s: string | null) =>
    s
      ? s.startsWith("upload:")
        ? s.slice(7)
        : s === "demo"
          ? "Demo dataset"
          : s === "manual"
            ? "Manual entry"
            : s
      : "";
  // "Modified = Y": the file's structured value replaced an AI-extracted one.
  const hasModification = (r: ReportDetail) =>
    (r.analysis?.modified_fields ?? []).some((m) => m.changed);
  const modifiedLabel = (r: ReportDetail) =>
    (r.analysis?.modified_fields ?? [])
      .filter((m) => m.changed)
      .map((m) => `${m.field} → “${m.used}” (AI: “${m.ai}”)`)
      .join(" · ");

  const sites = useMemo(() => Array.from(new Set(reports.map((r) => r.site).filter(Boolean))).sort(), [reports]);
  const activities = useMemo(
    () =>
      Array.from(
        new Set(reports.map((r) => r.analysis?.activity ?? r.activity).filter(Boolean))
      ).sort(),
    [reports]
  );

  const counts = useMemo(
    () => ({
      total: reports.length,
      sif: reports.filter((r) => r.analysis?.sif_potential).length,
      high: reports.filter((r) => r.analysis?.priority === "HIGH").length,
      pending: reports.filter((r) => r.review_status === "pending").length,
      reviewed: reports.filter((r) => r.review_status && r.review_status !== "pending").length,
    }),
    [reports]
  );

  // Quick-review shortcuts — each sets one view and clears the others.
  function setView(
    view: "all" | "sif" | "high" | "pending" | "reviewed",
  ) {
    setQ("");
    if (view === "all") {
      setSif("");
      setPriority("");
      setStatus("");
    } else if (view === "sif") {
      setSif("true");
      setPriority("");
      setStatus("");
    } else if (view === "high") {
      setSif("");
      setPriority("HIGH");
      setStatus("");
    } else if (view === "reviewed") {
      setSif("");
      setPriority("");
      setStatus("reviewed");
    } else {
      setSif("");
      setPriority("");
      setStatus("pending");
    }
  }

  async function trainOnLabels() {
    setTrainBusy(true);
    setTrainResult(null);
    try {
      const res = await api.trainOnFeedback();
      setTrainResult(res);
      setFb(await api.getFeedbackSummary());
      // Re-fetch so review counts stay fresh after labels are consumed.
      const data = await api.getReports({ limit: "10000" });
      setReports(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Training failed");
    } finally {
      setTrainBusy(false);
    }
  }

  const viewAll =
    sif === "" && priority === "" && status === "" && q === "";
  const viewSif = sif === "true" && priority === "" && status === "";
  const viewHigh = priority === "HIGH" && sif === "" && status === "";
  const viewPending = status === "pending" && sif === "" && priority === "";
  const viewReviewed = status === "reviewed" && sif === "" && priority === "";

  // Export exactly what the user sees (filters + search applied).
  const exportRows = filtered.map((r) => ({
    "Report ID": r.source_id ?? r.report_id,
    "File ID": r.source_id ?? "",
    "Source File": prettySource(r.source),
    "Modified (Y/N)": hasModification(r) ? "Y" : "N",
    Date: r.date ?? "",
    Type: r.report_type ?? "",
    Site: r.site ?? "",
    Activity: r.activity ?? r.analysis?.activity ?? "",
    "SIF-potential": r.analysis?.sif_potential ?? false,
    "Confidence (%)":
      r.analysis?.confidence != null ? Math.round(r.analysis.confidence * 100) : "",
    Priority: r.analysis?.priority ?? "",
    "Life-Saving Rule": r.analysis?.life_saving_rule ?? "",
    "Barrier Failure": r.analysis?.barrier_failure ?? [],
    Hazard: r.analysis?.hazard ?? "",
    "Review Status": r.review_status,
    "Report Text": r.report_text,
  }));

  return (
    <div className="animate-rise">
      <PageHeader
        kicker="Report Registry"
        title="SIF Reports"
        icon={FileText}
        lede="Every analyzed report — searchable, filterable, and ready for HSE review. Click any report to see the AI analysis with evidence and to confirm or correct the result."
        actions={
          <ExportButton
            rows={exportRows}
            filename="sif-reports"
            label="Export CSV"
          />
        }
      />

      {/* Review shortcuts */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="mr-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
          Review queue:
        </span>
        <FilterChip
          active={viewAll}
          onClick={() => setView("all")}
          label="All reports"
          count={counts.total}
        />
        <FilterChip
          active={viewSif}
          onClick={() => setView("sif")}
          label="SIF-potential"
          count={counts.sif}
          pink
        />
        <FilterChip
          active={viewHigh}
          onClick={() => setView("high")}
          label="High priority"
          count={counts.high}
          red
        />
        <FilterChip
          active={viewPending}
          onClick={() => setView("pending")}
          label="Pending HSE review"
          count={counts.pending}
          amber
        />
        <FilterChip
          active={viewReviewed}
          onClick={() => setView("reviewed")}
          label="HSE reviewed"
          count={counts.reviewed}
        />
        {!viewAll && (
          <button
            onClick={() => setView("all")}
            className="text-xs font-semibold text-brand-700 hover:underline"
          >
            Clear filters
          </button>
        )}

        {/* Human-in-the-loop training */}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={trainOnLabels}
            disabled={trainBusy || (fb?.labeled_for_training ?? 0) === 0}
            title="Re-measure model-vs-human agreement and learn signals from reviewed labels"
            className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700 transition hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {trainBusy ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <GraduationCap size={13} />
            )}
            Train on {fb?.labeled_for_training ?? 0} reviewed label
            {(fb?.labeled_for_training ?? 0) === 1 ? "" : "s"}
          </button>
          {fb && fb.feedback_count > 0 && (
            <span className="hidden text-[11px] text-ink-muted sm:inline">
              {fb.feedback_count} review{fb.feedback_count === 1 ? "" : "s"} stored
            </span>
          )}
        </div>
      </div>

      {fb?.latest_run && !trainResult && (
        <p className="mb-4 flex items-start gap-2 rounded-xl border border-violet-100 bg-violet-50/60 px-3.5 py-2.5 text-xs text-ink-soft">
          <BrainCircuit size={14} className="mt-0.5 flex-shrink-0 text-violet-600" />
          <span>
            <b className="text-violet-800">Latest training run:</b>{" "}
            {fb?.latest_run ? `${fb.latest_run.feedback_count} labels · agreement ${Math.round((fb.latest_run.metrics?.accuracy ?? 0) * 100)}% · F1 ${(fb.latest_run.metrics?.f1 ?? 0).toFixed(2)}` : "—"}
          </span>
        </p>
      )}
      {trainResult && (
        <div className="mb-4 flex flex-wrap items-start gap-x-4 gap-y-1 rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-xs text-ink-soft">
          <span className="inline-flex items-center gap-1.5 font-bold text-violet-800">
            <GraduationCap size={14} /> Training run #{trainResult.run_id}
          </span>
          <span>
            Labels: <b>{trainResult.feedback_count}</b>
          </span>
          <span>
            AI ↔ HSE agreement: <b>{trainResult.human_model_agreement}%</b>
          </span>
          <span>
            Precision <b>{trainResult.metrics.precision.toFixed(2)}</b> · Recall{" "}
            <b>{trainResult.metrics.recall.toFixed(2)}</b> · F1{" "}
            <b>{trainResult.metrics.f1.toFixed(2)}</b>
          </span>
          <span className="w-full text-violet-700">
            {trainResult.signals.length > 0 ? (
              <>
                Learned {trainResult.signals.length} signal
                {trainResult.signals.length === 1 ? "" : "s"} — future analyses
                quote them and flag for review (verdict never auto-flips):{" "}
                {trainResult.signals.slice(0, 3).map((s) => `“${s.phrase}”`).join(", ")}
                {trainResult.signals.length > 3 ? "…" : ""}
              </>
            ) : (
              "No new signals this run — reviewed labels agreed with the model."
            )}
          </span>
        </div>
      )}

      <div className="card">
        <div className="grid gap-3 md:grid-cols-4">
          <div className="relative md:col-span-2">
            <Search size={15} className="absolute left-3 top-3 text-ink-muted" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search report text…"
              className="w-full rounded-xl border border-brand-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-400"
            />
          </div>
          <select
            value={site}
            onChange={(e) => setSite(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All sites</option>
            {sites.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            value={activity}
            onChange={(e) => setActivity(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All activities</option>
            {activities.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p ? `Priority: ${p}` : "All priorities"}
              </option>
            ))}
          </select>
          <select
            value={rule}
            onChange={(e) => setRule(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All rules</option>
            {rules.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s ? `Status: ${s}` : "All statuses"}
              </option>
            ))}
          </select>
          <select
            value={sif}
            onChange={(e) => setSif(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">SIF: All</option>
            <option value="true">SIF: Yes</option>
            <option value="false">SIF: No</option>
          </select>
          <select
            value={file}
            onChange={(e) => setFile(e.target.value)}
            title="Filter by the file / dataset the report was imported from"
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All files</option>
            {files.map((f) => (
              <option key={f} value={f}>
                {prettySource(f)}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-2 text-xs text-ink-muted md:col-span-4">
            <SlidersHorizontal size={13} />
            {filtered.length} of {reports.length} reports
          </div>
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
            <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
          </div>
        )}

        <div className="table-wrap mt-4">
          <table className="w-full min-w-[1020px] text-left text-sm">
            <thead>
              <tr className="table-head">
                <th className="px-4 py-3 font-semibold">Report ID</th>
                <th className="px-4 py-3 font-semibold">File ID</th>
                <th className="px-4 py-3 font-semibold">Source file</th>
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Site</th>
                <th className="px-4 py-3 font-semibold">Activity</th>
                <th className="px-4 py-3 font-semibold">SIF</th>
                <th className="px-4 py-3 font-semibold">Priority</th>
                <th className="px-4 py-3 font-semibold">Life-Saving Rule</th>
                <th className="px-4 py-3 font-semibold">Barrier Failure</th>
                <th className="px-4 py-3 font-semibold">Mod.</th>
                <th className="px-4 py-3 font-semibold">Review</th>
                <th className="px-4 py-3 font-semibold">View</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={13} className="px-4 py-12 text-center">
                    <Loader2 className="mx-auto animate-spin text-brand-500" size={24} />
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={13} className="px-4 py-12 text-center text-sm text-ink-muted">
                    No reports match the current filters.
                  </td>
                </tr>
              ) : (
                filtered.map((r) => (
                  <tr key={r.id} className="table-row">
                    <td className="px-4 py-3">
                      <Link
                        href={`/reports/${r.id}`}
                        className="font-mono text-xs font-semibold text-brand-700 hover:underline"
                      >
                        {r.source_id ?? r.report_id}
                      </Link>
                      {r.is_demo && (
                        <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-700">
                          demo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink-soft">
                      {r.source_id ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-soft">
                      {r.source ? (
                        <span
                          className="inline-block max-w-[150px] truncate align-middle"
                          title={prettySource(r.source)}
                        >
                          {prettySource(r.source)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-soft">{r.date ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-ink-soft">{r.site ?? "—"}</td>
                    <td className="px-4 py-3 text-xs text-ink-soft">
                      {r.activity ?? r.analysis?.activity ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <SifBadge sif={r.analysis?.sif_potential ?? false} />
                    </td>
                    <td className="px-4 py-3">
                      <PriorityBadge priority={r.analysis?.priority ?? null} />
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-soft">
                      {r.analysis?.life_saving_rule ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-soft">
                      {r.analysis?.barrier_failure?.length
                        ? r.analysis.barrier_failure.slice(0, 2).join(", ")
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {hasModification(r) ? (
                        <span
                          title={`File value replaced AI extraction — ${modifiedLabel(r)}`}
                          className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-[10px] font-extrabold text-amber-700"
                        >
                          Y
                        </span>
                      ) : (
                        <span className="text-xs text-ink-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <ReviewBadge status={r.review_status} />
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/reports/${r.id}`}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 shadow-sm transition hover:border-brand-300 hover:bg-brand-50"
                      >
                        <Eye size={12} /> View
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function FilterChip({
  label,
  count,
  active,
  onClick,
  pink,
  red,
  amber,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  pink?: boolean;
  red?: boolean;
  amber?: boolean;
}) {
  const tone = active
    ? pink
      ? "border-brand-500 bg-brand-600 text-white shadow-sm"
      : red
        ? "border-red-500 bg-red-600 text-white shadow-sm"
        : amber
          ? "border-amber-500 bg-amber-500 text-white shadow-sm"
          : "border-ink text-white bg-ink"
    : "border-brand-200 bg-white text-ink-soft hover:border-brand-300 hover:bg-brand-50";
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${tone}`}
    >
      {label}
      <span
        className={`rounded-full px-1.5 text-[10px] font-bold ${
          active ? "bg-white/25 text-white" : "bg-brand-100 text-brand-700"
        }`}
      >
        {count}
      </span>
    </button>
  );
}