"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  BrainCircuit,
  CopyCheck,
  Eye,
  FileText,
  GraduationCap,
  Loader2,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import type { FeedbackSummary, ReportDetail, ReviewStatus, TrainResponse } from "@/lib/api";
import { api } from "@/lib/api";
import {
  isVerified,
  PriorityBadge,
  ReviewBadge,
  REVIEW_LABELS,
  SifBadge,
} from "@/components/Badges";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

const PRIORITIES = ["", "HIGH", "MEDIUM", "LOW"];
// "verified" is a pseudo-status = any decision an HSE professional made
// (confirmed / reviewed / edited) — handy for the queue chips.
type StatusFilter = ReviewStatus | "" | "verified";
const STATUSES: StatusFilter[] = [
  "",
  "verified",
  "pending",
  "confirmed",
  "reviewed",
  "edited",
  "rejected",
];

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
  const [rtype, setRtype] = useState("");
  const [hazard, setHazard] = useState("");
  const [barrier, setBarrier] = useState("");
  const [dupOnly, setDupOnly] = useState(false);

  // Human-in-the-loop: reviewed labels + "train" action.
  const [fb, setFb] = useState<FeedbackSummary | null>(null);
  const [trainBusy, setTrainBusy] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResponse | null>(null);

  useEffect(() => {
    // Support deep links: ?priority=HIGH (dashboard review queue),
    // ?file=<source> (one imported file) and ?rule=/?activity=/?hazard=/
    // ?barrier= (used by Recurring Patterns / Barrier cards to open the
    // real report set behind a pattern).
    const params = new URLSearchParams(window.location.search);
    if (params.get("priority") === "HIGH") setPriority("HIGH");
    const f = params.get("file");
    if (f) setFile(f);
    const rl = params.get("rule");
    if (rl) setRule(rl);
    const ac = params.get("activity");
    if (ac) setActivity(ac);
    const hz = params.get("hazard");
    if (hz) setHazard(hz);
    const br = params.get("barrier");
    if (br) setBarrier(br);
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

  // Distinct hazard + barrier values (used by the pattern deep links and the
  // filter dropdowns).
  const hazardOptions = useMemo(
    () =>
      Array.from(
        new Set(reports.map((r) => r.analysis?.hazard).filter((h): h is string => !!h))
      ).sort(),
    [reports]
  );
  const barrierOptions = useMemo(() => {
    const set = new Set<string>();
    reports.forEach((r) =>
      (r.analysis?.barrier_failure ?? []).forEach((b) => set.add(b))
    );
    return Array.from(set).sort();
  }, [reports]);

  // Report categories found in the dataset (e.g. Unsafe Act / Unsafe
  // Condition / Near Miss / Incident) — filterable like site & activity.
  const reportTypes = useMemo(
    () =>
      Array.from(
        new Set(reports.map((r) => r.report_type).filter((t): t is string => !!t))
      ).sort(),
    [reports]
  );

  // Duplicate indication: rows whose normalized text is stored more than once
  // (same incident re-reported, or a file imported twice). Cheap client-side
  // fingerprint — the report detail page adds semantic near-copy detection.
  const dupGroups = useMemo(() => {
    const byText = new Map<string, number[]>();
    const idToReport = new Map(reports.map((r) => [r.id, r]));
    for (const r of reports) {
      const key = r.report_text
        .toLowerCase()
        .replace(/[^a-z0-9\u0900-\u09ff]+/g, " ")
        .trim();
      if (key.length < 8) continue;
      const arr = byText.get(key) ?? [];
      arr.push(r.id);
      byText.set(key, arr);
    }
    const out = new Map<number, { count: number; others: string[] }>();
    for (const ids of byText.values()) {
      if (ids.length < 2) continue;
      for (const id of ids) {
        const others = ids
          .filter((x) => x !== id)
          .map((x) => idToReport.get(x)?.report_id ?? String(x));
        out.set(id, { count: ids.length, others });
      }
    }
    return out;
  }, [reports]);

  const filtered = useMemo(() => {
    return reports.filter((r) => {
      // Field search: match across the narrative, IDs, site, activity, type,
      // Life-Saving Rule and hazard — not just the report text.
      if (
        q &&
        ![
          r.report_text,
          r.report_id,
          r.source_id ?? "",
          r.site ?? "",
          r.activity ?? "",
          r.report_type ?? "",
          r.analysis?.life_saving_rule ?? "",
          r.analysis?.hazard ?? "",
        ]
          .join(" ")
          .toLowerCase()
          .includes(q.toLowerCase())
      )
        return false;
      if (rtype && (r.report_type ?? "") !== rtype) return false;
      if (dupOnly && !dupGroups.has(r.id)) return false;
      if (site && r.site !== site) return false;
      if (activity && (r.analysis?.activity ?? r.activity) !== activity) return false;
      if (hazard && r.analysis?.hazard !== hazard) return false;
      if (barrier) {
        const hits = (r.analysis?.barrier_failure ?? []).some((b) =>
          b.toLowerCase().includes(barrier.toLowerCase())
        );
        if (!hits) return false;
      }
      if (priority && r.analysis?.priority !== priority) return false;
      if (rule && r.analysis?.life_saving_rule !== rule) return false;
      if (status === "verified") {
        if (!isVerified(r.review_status)) return false;
      } else if (status && r.review_status !== status) return false;
      if (file && r.source !== file) return false;
      if (sif === "true" && !r.analysis?.sif_potential) return false;
      if (sif === "false" && r.analysis?.sif_potential) return false;
      return true;
    });
  }, [reports, q, site, activity, hazard, barrier, priority, rule, status, sif, file, rtype, dupOnly, dupGroups]);

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
      // "Needs HSE review" only counts analyzed rows without a decision;
      // rows the pipeline failed to analyze are shown separately.
      pending: reports.filter(
        (r) => r.processing_status === "analyzed" && r.review_status === "pending"
      ).length,
      verified: reports.filter((r) => isVerified(r.review_status)).length,
      rejected: reports.filter((r) => r.review_status === "rejected").length,
      duplicates: reports.filter((r) => dupGroups.has(r.id)).length,
    }),
    [reports, dupGroups]
  );

  // Quick-review shortcuts — each sets one view and clears the others.
  function setView(
    view: "all" | "sif" | "high" | "pending" | "verified" | "rejected" | "duplicates",
  ) {
    setQ("");
    setDupOnly(false);
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
    } else if (view === "verified") {
      setSif("");
      setPriority("");
      setStatus("verified");
    } else if (view === "rejected") {
      setSif("");
      setPriority("");
      setStatus("rejected");
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
  const viewVerified = status === "verified" && sif === "" && priority === "";
  const viewRejected = status === "rejected" && sif === "" && priority === "";

  // Export exactly what the user sees (filters + search applied). The system
  // Report ID and the file's Actual ID stay distinct, and the Status column is
  // explicit — rows the pipeline could not analyze are not shown as "pending".
  const exportRows = filtered.map((r) => ({
    "Report ID": r.report_id,
    "Actual ID (file)": r.source_id ?? "",
    "Source File": prettySource(r.source),
    Status:
      r.processing_status === "failed"
        ? "Analysis failed"
        : REVIEW_LABELS[r.review_status],
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
          active={viewVerified}
          onClick={() => setView("verified")}
          label="HSE verified"
          count={counts.verified}
          green
        />
        <FilterChip
          active={viewRejected}
          onClick={() => setView("rejected")}
          label="Rejected · not SIF"
          count={counts.rejected}
          orange
        />
        <FilterChip
          active={dupOnly}
          onClick={() => {
            if (dupOnly) {
              setDupOnly(false);
            } else {
              setView("all");
              setDupOnly(true);
            }
          }}
          label="Possible duplicates"
          count={counts.duplicates}
          violet
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
              placeholder="Search text, ID, site, activity, rule…"
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
            value={hazard}
            onChange={(e) => setHazard(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All hazards</option>
            {hazardOptions.map((h) => (
              <option key={h}>{h}</option>
            ))}
          </select>
          <select
            value={barrier}
            onChange={(e) => setBarrier(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All barrier failures</option>
            {barrierOptions.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s
                  ? `Status: ${s === "verified" ? "HSE checked (any)" : REVIEW_LABELS[s]}`
                  : "All statuses"}
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
            value={rtype}
            onChange={(e) => setRtype(e.target.value)}
            title="Filter by report category from the source file (e.g. Unsafe Act / Unsafe Condition / Near Miss / Incident)"
            className="rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
          >
            <option value="">All report types</option>
            {reportTypes.map((t) => (
              <option key={t}>{t}</option>
            ))}
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
                <th
                  className="px-4 py-3 font-semibold"
                  title="System Report ID — generated by the platform, unique for every report"
                >
                  Report ID
                </th>
                <th
                  className="px-4 py-3 font-semibold"
                  title="Actual ID — the report's own ID as it appeared in the imported file"
                >
                  Actual ID
                </th>
                <th className="px-4 py-3 font-semibold">Source file</th>
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Site</th>
                <th className="px-4 py-3 font-semibold">Activity</th>
                <th className="px-4 py-3 font-semibold">SIF</th>
                <th className="px-4 py-3 font-semibold">Priority</th>
                <th className="px-4 py-3 font-semibold">Life-Saving Rule</th>
                <th className="px-4 py-3 font-semibold">Barrier Failure</th>
                <th
                  className="px-4 py-3 font-semibold"
                  title="Possible duplicate — the same report text stored more than once (re-reported incident / file imported twice)"
                >
                  Dup.
                </th>
                <th
                  className="px-4 py-3 font-semibold"
                  title="HSE review state — rows the pipeline could not analyze show as failed"
                >
                  Status
                </th>
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
                filtered.map((r) => {
                  const dupInfo = dupGroups.get(r.id);
                  return (
                  <tr key={r.id} className="table-row">
                    <td className="px-4 py-3">
                      <Link
                        href={`/reports/${r.id}`}
                        title={`System Report ID ${r.report_id} — opens this report`}
                        className="font-mono text-xs font-semibold text-brand-700 hover:underline"
                      >
                        {r.report_id}
                      </Link>
                      {r.is_demo && (
                        <span className="ml-2 rounded-full border border-amber-300/70 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-700">
                          demo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {r.source_id ? (
                        <span
                          className="font-mono font-semibold text-ink"
                          title={`Actual ID — this report's own ID in its source file (${prettySource(r.source)})`}
                        >
                          {r.source_id}
                        </span>
                      ) : (
                        <span className="text-ink-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {r.source ? (
                        <button
                          type="button"
                          onClick={() =>
                            setFile(file === r.source ? "" : r.source!)
                          }
                          title={
                            file === r.source
                              ? "Showing only this file — click again to show all files"
                              : `View all reports imported from ${prettySource(r.source)}`
                          }
                          aria-pressed={file === r.source}
                          className={`inline-flex max-w-[170px] items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold transition ${
                            file === r.source
                              ? "border-brand-600 bg-brand-600 text-white"
                              : "border-brand-200 bg-brand-50 text-brand-700 hover:border-brand-400 hover:bg-brand-100"
                          }`}
                        >
                          <FileText size={10} className="flex-shrink-0" />
                          <span className="truncate">
                            {prettySource(r.source)}
                          </span>
                        </button>
                      ) : (
                        <span className="text-xs text-ink-muted">—</span>
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
                    </td>
                    <td className="px-4 py-3">
                      {dupInfo ? (
                        <span
                          className="badge badge-orange"
                          title={`Possible duplicate — the same report text appears ${dupInfo.count} times in this dataset (also: ${dupInfo.others.join(", ")}). Review before duplicating any corrective action.`}
                        >
                          <CopyCheck size={11} /> ×{dupInfo.count}
                        </span>
                      ) : (
                        <span className="text-xs text-ink-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {r.processing_status === "failed" ? (
                        <span
                          className="badge badge-red"
                          title="The AI pipeline could not analyze this row — open it, check the raw text and re-run the analysis"
                        >
                          Analysis failed
                        </span>
                      ) : (
                        <ReviewBadge status={r.review_status} />
                      )}
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
                  );
                })
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
  green,
  orange,
  violet,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  pink?: boolean;
  red?: boolean;
  amber?: boolean;
  green?: boolean;
  orange?: boolean;
  violet?: boolean;
}) {
  const activeTone = pink
    ? "border-brand-600 bg-brand-600 text-white shadow-sm"
    : red
      ? "border-red-600 bg-red-600 text-white shadow-sm"
      : amber
        ? "border-amber-500 bg-amber-500 text-white shadow-sm"
        : green
          ? "border-green-600 bg-green-600 text-white shadow-sm"
          : orange
            ? "border-orange-600 bg-orange-600 text-white shadow-sm"
            : violet
              ? "border-violet-600 bg-violet-600 text-white shadow-sm"
              : "border-ink bg-ink text-white";
  const tone = active
    ? activeTone
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