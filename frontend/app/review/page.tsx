"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeCheck,
  CheckCircle2,
  ClipboardCheck,
  FileWarning,
  Loader2,
  ShieldAlert,
  ThumbsDown,
  UserRound,
} from "lucide-react";
import type { ReportDetail, ReviewStatus } from "@/lib/api";
import { api } from "@/lib/api";
import { PriorityBadge, ReviewBadge } from "@/components/Badges";
import PageHeader from "@/components/PageHeader";

type QueueView = "pending" | "verified" | "rejected" | "all";

/**
 * Dedicated HSE Reviewer workspace — separate from the general Reports
 * registry so reviewers are never confused by search/export/admin controls.
 * Only two jobs happen here: decide (verify / reject / edit) and hand off to
 * the full report page when a correction is needed.
 */
export default function ReviewPage() {
  const [reports, setReports] = useState<ReportDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [view, setView] = useState<QueueView>("pending");
  const [reviewer, setReviewer] = useState("HSE Reviewer");
  const [justActed, setJustActed] = useState<string | null>(null);

  function load() {
    api
      .getReports({ limit: "10000" })
      .then((data) => {
        setReports(data);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    const onVisible = () => {
      if (document.visibilityState === "visible") load();
    };
    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  const needsReview = (r: ReportDetail) =>
    r.processing_status === "analyzed" && r.review_status === "pending";

  const counts = useMemo(() => {
    let pending = 0;
    let verified = 0;
    let rejected = 0;
    let failed = 0;
    for (const r of reports) {
      if (r.processing_status === "failed") failed += 1;
      if (needsReview(r)) pending += 1;
      else if (r.review_status === "rejected") rejected += 1;
      else if (
        r.review_status === "confirmed" ||
        r.review_status === "reviewed" ||
        r.review_status === "edited"
      )
        verified += 1;
    }
    return { pending, verified, rejected, failed, total: reports.length };
  }, [reports]);

  const queue = useMemo(() => {
    const visible = reports.filter((r) => {
      if (view === "pending") return needsReview(r);
      if (view === "verified")
        return (
          r.review_status === "confirmed" ||
          r.review_status === "reviewed" ||
          r.review_status === "edited"
        );
      if (view === "rejected") return r.review_status === "rejected";
      return true;
    });
    // High-priority / SIF-potential first, then newest first.
    const rank = (r: ReportDetail) => {
      const p = r.analysis?.priority === "HIGH" ? 0 : r.analysis?.priority === "MEDIUM" ? 1 : 2;
      return p * 100 + (r.analysis?.sif_potential ? 0 : 10);
    };
    return [...visible].sort(
      (a, b) => rank(a) - rank(b) || String(b.date ?? "").localeCompare(String(a.date ?? ""))
    );
  }, [reports, view]);

  async function decide(r: ReportDetail, decision: "confirmed" | "rejected") {
    setBusyId(r.id);
    setJustActed(null);
    try {
      const res = await api.reviewReport(r.id, {
        reviewer: reviewer || undefined,
        decision,
        comments: undefined,
        mark_reviewed: true,
      });
      setReports((prev) =>
        prev.map((x) => (x.id === r.id ? { ...x, review_status: res.report.review_status } : x))
      );
      setJustActed(
        decision === "confirmed"
          ? `${r.report_id} verified as SIF-potential`
          : `${r.report_id} marked not SIF-potential`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="animate-rise">
      <PageHeader
        kicker="HSE Reviewer Workspace"
        title="Review Queue"
        icon={ClipboardCheck}
        lede={
          <>
            A focused inbox for the HSE team — separate from the Reports
            registry. Every report here carries an AI verdict that still needs a
            human decision. Your confirm / reject actions are stored as labeled
            feedback for model evaluation.
          </>
        }
        actions={
          <label className="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-2 text-xs font-semibold text-ink-soft">
            <UserRound size={13} className="text-brand-600" />
            Reviewer
            <input
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              className="w-32 bg-transparent text-xs font-semibold text-ink outline-none focus:border-b focus:border-brand-400"
              placeholder="Your name"
            />
          </label>
        }
      />

      {justActed && (
        <p className="mb-4 flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-4 py-2.5 text-sm font-semibold text-green-700">
          <BadgeCheck size={15} /> {justActed} — removed from the pending queue.
        </p>
      )}
      {error && (
        <p className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
          <ShieldAlert size={15} /> {error}
        </p>
      )}

      {/* Queue KPI strip */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <QueueStat
          label="Awaiting HSE decision"
          value={counts.pending}
          tone="amber"
          active={view === "pending"}
          onClick={() => setView("pending")}
          hint="AI verdict ready — no human check yet"
        />
        <QueueStat
          label="Verified by HSE"
          value={counts.verified}
          tone="green"
          active={view === "verified"}
          onClick={() => setView("verified")}
          hint="Confirmed, reviewed or edited by HSE"
        />
        <QueueStat
          label="Rejected · not SIF"
          value={counts.rejected}
          tone="orange"
          active={view === "rejected"}
          onClick={() => setView("rejected")}
          hint="HSE overruled the AI SIF verdict"
        />
        <QueueStat
          label="Analysis failed"
          value={counts.failed}
          tone="red"
          active={false}
          onClick={() => setView("all")}
          hint="Pipeline could not analyze — open and re-run"
        />
      </div>

      <div className="card mt-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-100 pb-3">
          <h2 className="card-title">
            {view === "pending" && "Reports needing a decision"}
            {view === "verified" && "Reports verified by HSE"}
            {view === "rejected" && "Rejected SIF verdicts"}
            {view === "all" && "All reports"}
            <span className="badge badge-gray">{queue.length}</span>
          </h2>
          <span className="text-xs text-ink-muted">
            Sorted: high priority first, then newest
          </span>
        </div>

        {loading ? (
          <div className="grid place-items-center py-20">
            <Loader2 className="animate-spin text-brand-500" size={24} />
          </div>
        ) : queue.length === 0 ? (
          <div className="py-14 text-center">
            {view === "pending" ? (
              <>
                <p className="text-lg font-bold text-ink">Queue is clear 🎉</p>
                <p className="mx-auto mt-1 max-w-md text-sm text-ink-muted">
                  Every analyzed report has an HSE decision. Import a new
                  dataset or analyze a single report to create new work here.
                </p>
                <Link href="/ingest" className="btn-ghost mt-4">
                  Import a dataset
                </Link>
              </>
            ) : (
              <p className="text-sm text-ink-muted">
                No reports in this view.
              </p>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-brand-50">
            {queue.map((r) => {
              const a = r.analysis;
              const isPending = needsReview(r);
              return (
                <li key={r.id} className="py-4 first:pt-2 last:pb-2">
                  <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={`/reports/${r.id}`}
                          className="font-mono text-sm font-bold text-brand-700 hover:underline"
                        >
                          {r.report_id}
                        </Link>
                        {r.site && (
                          <span className="text-xs text-ink-muted">{r.site}</span>
                        )}
                        {r.date && (
                          <span className="text-xs text-ink-muted">{r.date}</span>
                        )}
                        {!isPending && <ReviewBadge status={r.review_status} />}
                      </div>
                      <p
                        className="mt-1.5 line-clamp-2 max-w-3xl text-[13px] leading-relaxed text-ink-soft"
                        title={r.report_text}
                      >
                        {r.report_text}
                      </p>
                      {a && (
                        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                          <SifChip sif={a.sif_potential} />
                          <PriorityBadge priority={a.priority} />
                          {a.life_saving_rule && (
                            <span className="rounded-full border border-brand-100 bg-brand-50 px-2 py-0.5 font-semibold text-brand-700">
                              {a.life_saving_rule}
                            </span>
                          )}
                          {a.confidence != null && (
                            <span className="text-ink-muted">
                              confidence {Math.round(a.confidence * 100)}%
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {isPending ? (
                      <div className="flex flex-shrink-0 items-center gap-2">
                        <button
                          onClick={() => decide(r, "confirmed")}
                          disabled={busyId === r.id}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-green-300 bg-green-50 px-3 py-2 text-xs font-bold text-green-700 transition hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-50"
                          title="Confirm the AI SIF-potential verdict — this counts as HSE verified"
                        >
                          {busyId === r.id ? (
                            <Loader2 size={13} className="animate-spin" />
                          ) : (
                            <CheckCircle2 size={13} />
                          )}
                          Verify as SIF
                        </button>
                        <button
                          onClick={() => decide(r, "rejected")}
                          disabled={busyId === r.id}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-orange-200 bg-white px-3 py-2 text-xs font-bold text-orange-700 transition hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-50"
                          title="Reject the AI SIF verdict — treated as not SIF-potential"
                        >
                          <ThumbsDown size={13} />
                          Not SIF
                        </button>
                        <Link
                          href={`/reports/${r.id}`}
                          title="Open the full report — edit priority / rule or add a comment, then submit"
                          className="inline-flex items-center gap-1 rounded-lg border border-brand-200 bg-white px-3 py-2 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
                        >
                          <ArrowUpRight size={13} /> Review
                        </Link>
                      </div>
                    ) : (
                      <Link
                        href={`/reports/${r.id}`}
                        className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-brand-200 bg-white px-3 py-2 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
                      >
                        Open record <ArrowUpRight size={13} />
                      </Link>
                    )}
                  </div>
                  {r.processing_status === "failed" && (
                    <p className="mt-2 flex items-center gap-1.5 text-[11px] font-semibold text-red-600">
                      <FileWarning size={12} />
                      Analysis failed for this row — open it and use “Re-run AI
                      analysis”.
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function SifChip({ sif }: { sif: boolean }) {
  return sif ? (
    <span className="badge badge-pink">SIF-potential</span>
  ) : (
    <span className="badge badge-gray">non-SIF</span>
  );
}

function QueueStat({
  label,
  value,
  tone,
  active,
  onClick,
  hint,
}: {
  label: string;
  value: number;
  tone: "amber" | "green" | "orange" | "red";
  active: boolean;
  onClick: () => void;
  hint: string;
}) {
  const toneBg =
    tone === "amber"
      ? "bg-amber-100 text-amber-700"
      : tone === "green"
        ? "bg-green-100 text-green-700"
        : tone === "orange"
          ? "bg-orange-100 text-orange-700"
          : "bg-red-100 text-red-700";
  return (
    <button
      onClick={onClick}
      title={hint}
      aria-pressed={active}
      className={`card flex items-start justify-between gap-3 !p-4 text-left transition ${
        active ? "ring-2 ring-brand-300" : "hover:border-brand-300"
      }`}
    >
      <span>
        <span className="block text-[10px] font-bold uppercase tracking-wider text-ink-muted">
          {label}
        </span>
        <span className="mt-1 block text-3xl font-extrabold tracking-tight text-ink">
          {value}
        </span>
        <span className="mt-1 block text-[10px] text-ink-muted">{hint}</span>
      </span>
      <span className={`grid h-8 w-8 place-items-center rounded-full ${toneBg}`}>
        <span className="text-sm font-extrabold">{value}</span>
      </span>
    </button>
  );
}

// Keep the ReviewStatus import referenced for future edits of this queue.
export type { ReviewStatus };
