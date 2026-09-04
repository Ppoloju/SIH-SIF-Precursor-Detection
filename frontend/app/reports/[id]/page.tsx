"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  FileText,
  GitCompare,
  Loader2,
  MessageSquare,
  PenLine,
  RefreshCw,
  ThumbsDown,
  UserRound,
} from "lucide-react";
import type { ReportDetail } from "@/lib/api";
import { api } from "@/lib/api";
import AnalysisResultCard from "@/components/AnalysisResultCard";
import { PriorityBadge, ReviewBadge } from "@/components/Badges";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [reviewer, setReviewer] = useState("HSE Reviewer");
  const [comment, setComment] = useState("");
  const [decision, setDecision] = useState<"confirmed" | "rejected" | "edited">();
  const [correctedPriority, setCorrectedPriority] = useState<"HIGH" | "MEDIUM" | "LOW">();
  const [correctedRule, setCorrectedRule] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .getReport(params.id)
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }

  useEffect(load, [params.id]);

  async function submitReview() {
    if (!report) return;
    setBusy(true);
    try {
      const res = await api.reviewReport(report.id, {
        reviewer: reviewer || undefined,
        decision,
        corrected_priority: correctedPriority,
        corrected_rule: correctedRule || undefined,
        comments: comment || undefined,
        mark_reviewed: true,
      });
      setReport(res.report);
      setComment("");
      setDecision(undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setBusy(false);
    }
  }

  async function runReanalysis() {
    if (!report) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.reanalyzeReport(report.id);
      setReport(updated);
      setComment("");
      setDecision(undefined);
      setCorrectedPriority(undefined);
      setCorrectedRule("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Re-analysis failed");
    } finally {
      setBusy(false);
    }
  }

  if (error && !report) {
    return (
      <div className="card mx-auto max-w-xl">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 text-red-500" size={20} />
          <div>
            <h1 className="text-lg font-bold">Report unavailable</h1>
            <p className="mt-1 text-sm text-ink-muted">{error}</p>
            <Link href="/reports" className="btn-ghost mt-4">
              <ArrowLeft size={15} /> Back to reports
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="grid place-items-center py-32">
        <Loader2 className="animate-spin text-brand-500" size={26} />
      </div>
    );
  }

  const a = report.analysis;
  const result = a
    ? {
        sif_potential: a.sif_potential,
        confidence: a.confidence,
        priority: a.priority,
        hazard: a.hazard,
        hazards: a.hazard ? [a.hazard] : [],
        potential_consequence: a.potential_consequence,
        barrier_failure: a.barrier_failure ?? [],
        life_saving_rule: a.life_saving_rule,
        activity: a.activity,
        location: a.location ?? null,
        equipment: a.equipment ?? [],
        unsafe_type: a.unsafe_type ?? report.report_type ?? null,
        evidence: a.evidence ?? [],
        rule_conditions: a.rule_conditions ?? [],
        explanation: a.explanation,
        recommended_follow_up: a.recommended_follow_up,
        summary: a.summary,
        suggested_actions: a.suggested_actions ?? [],
        languages: a.languages ?? [],
        model: a.model,
        llm_refined: false,
        uncertainty_note: a.uncertainty_note,
        priority_factors: {},
      }
    : null;

  return (
    <div className="mx-auto max-w-5xl animate-rise">
      <Link
        href="/reports"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline"
      >
        <ArrowLeft size={15} /> All reports
      </Link>

      <div className="relative mt-4 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-white p-5 shadow-soft sm:p-6">
        <div className="pointer-events-none absolute -right-16 -top-24 h-52 w-52 rounded-full bg-brand-200/40 blur-3xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-4">
            <span className="grid h-12 w-12 flex-shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
              <FileText size={22} />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="font-mono text-2xl font-extrabold tracking-tight">
                  {report.source_id ?? report.report_id}
                </h1>
                <ReviewBadge status={report.review_status} />
                {report.is_demo ? (
                  <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-600">
                    Demo / Synthetic Data
                  </span>
                ) : report.source && report.source !== "manual" ? (
                  <span className="rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 text-[10px] font-bold uppercase text-brand-600">
                    Imported · {report.source.replace("upload:", "").slice(0, 28)}
                  </span>
                ) : null}
              </div>
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                <MetaChip label="Type" value={report.report_type ?? "Report"} />
                <MetaChip label="Date" value={report.date ?? "not set"} />
                <MetaChip label="Site" value={report.site ?? "not set"} />
                {a?.activity && <MetaChip label="Activity" value={a.activity} />}
                {report.source_id && (
                  <MetaChip label="File ID" value={report.source_id} />
                )}
              </div>
            </div>
          </div>
          {a && (
            <div className="flex flex-col items-start gap-1.5 rounded-2xl border border-brand-100 bg-white/80 px-4 py-3 shadow-soft sm:items-end">
              <PriorityBadge priority={a.priority} />
              <span className="text-[11px] font-semibold text-ink-muted">
                AI confidence{" "}
                {a.confidence != null ? Math.round(a.confidence * 100) : "—"}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* File-provided values that replaced the AI extraction (crosscheck) */}
      {a?.modified_fields && a.modified_fields.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 text-xs leading-relaxed text-amber-900">
          <p className="flex flex-wrap items-center gap-1.5 font-bold uppercase tracking-wider text-amber-800">
            <PenLine size={12} /> File data used &amp; crosschecked
          </p>
          <ul className="mt-1.5 space-y-1">
            {a.modified_fields.map((m) => (
              <li key={`${m.field}-${m.used}`}>
                <b className="capitalize">{m.field.replace("_", " ")}</b>: file says{" "}
                “{m.used}”
                {m.changed && m.ai ? (
                  <>
                    {" "}
                    <span className="font-semibold">— Modified = Y</span> (AI had
                    extracted “{m.ai}”)
                  </>
                ) : (
                  <span> — taken from the file</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="card">
            <h2 className="card-title text-brand-600">Original Report</h2>
            <p className="mt-2 whitespace-pre-wrap rounded-xl bg-brand-50/60 p-4 text-sm leading-relaxed text-ink-soft">
              {report.report_text}
            </p>
          </div>

          {result && <AnalysisResultCard result={result} heading={`AI Analysis — ${report.source_id ?? report.report_id}`} />}

          {report.similar_reports.length > 0 && (
            <div className="card">
              <h2 className="card-title">
                <GitCompare size={16} className="text-brand-600" /> Similar Historical
                Reports
              </h2>
          <p className="mt-1 text-xs text-ink-muted">
            Reports sharing the same hazard, activity or barrier signals — a
            fast way to see whether this precursor has appeared before. Click
            a row to open the related report.
          </p>
              <ul className="mt-3 space-y-2">
                {report.similar_reports.map((sr) => (
                  <li key={sr.report_id}>
                    <Link
                      href={`/reports/${sr.id}`}
                      className="group flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-brand-100 bg-brand-50/40 px-3.5 py-2.5 transition hover:border-brand-300 hover:bg-brand-100/60"
                    >
                      <span className="font-mono text-xs font-bold text-brand-700">
                        {sr.report_id}
                      </span>
                      <span className="ml-auto badge badge-pink">
                        {Math.round(sr.similarity * 100)}% similar
                      </span>
                      <span className="w-full text-[11px] text-ink-muted">
                        {[sr.common_hazard, sr.common_activity, sr.common_rule]
                          .filter(Boolean)
                          .join(" · ") || "Shared precursor context"}
                      </span>
                      <span className="text-[11px] font-bold text-brand-600 opacity-0 transition group-hover:opacity-100">
                        Open →
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report.review && (
            <div className="card">
              <h2 className="card-title">
                <UserRound size={16} className="text-brand-600" /> HSE Review Record
              </h2>
              <div className="mt-3 space-y-2 text-sm">
                <p>
                  <b>Reviewer:</b> {report.review.reviewer ?? "—"}
                </p>
                <p>
                  <b>Decision:</b>{" "}
                  <span className="font-semibold capitalize">{report.review.decision ?? "—"}</span>
                </p>
                {report.review.corrected_priority && (
                  <p>
                    <b>Corrected priority:</b> {report.review.corrected_priority}
                  </p>
                )}
                {report.review.corrected_rule && (
                  <p>
                    <b>Corrected Life-Saving Rule:</b> {report.review.corrected_rule}
                  </p>
                )}
                {report.review.comments && (
                  <p className="rounded-xl bg-brand-50/60 p-3 text-ink-soft">
                    “{report.review.comments}”
                  </p>
                )}
                <p className="text-xs text-ink-muted">
                  Reviewed at {report.review.reviewed_at ?? "—"}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* HSE review panel */}
        <div className="card h-fit">
          <h2 className="card-title">
            <PenLine size={16} className="text-brand-600" /> HSE Review
          </h2>
          <p className="mt-1 text-xs text-ink-muted">
            AI assists the HSE professional — you make the final call. Feedback
            is stored for future model improvement.
          </p>

          <button
            onClick={runReanalysis}
            disabled={busy}
            className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-xl border border-brand-200 bg-white px-3 py-2 text-xs font-bold text-brand-700 transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
            title="Re-run the AI pipeline on this report and update the stored analysis"
          >
            {busy ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <RefreshCw size={13} />
            )}
            Re-run AI analysis
          </button>
          <p className="mt-1.5 text-[11px] text-ink-muted">
            Re-processes this report, updates the database result and resets the
            review state.
          </p>

          <hr className="my-4 border-brand-100" />

          <label className="mt-4 block text-xs font-bold uppercase tracking-wider text-ink-muted">
            Reviewer
          </label>
          <input
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-400"
          />

          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              onClick={() => setDecision("confirmed")}
              className={`flex items-center justify-center gap-1.5 rounded-xl border px-3 py-2.5 text-sm font-semibold transition ${
                decision === "confirmed"
                  ? "border-green-500 bg-green-50 text-green-700"
                  : "border-brand-200 bg-white text-ink-soft hover:bg-green-50"
              }`}
            >
              <CheckCircle2 size={15} /> Confirm SIF
            </button>
            <button
              onClick={() => setDecision("rejected")}
              className={`flex items-center justify-center gap-1.5 rounded-xl border px-3 py-2.5 text-sm font-semibold transition ${
                decision === "rejected"
                  ? "border-orange-500 bg-orange-50 text-orange-700"
                  : "border-brand-200 bg-white text-ink-soft hover:bg-orange-50"
              }`}
            >
              <ThumbsDown size={15} /> Reject SIF
            </button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                Priority
              </label>
              <select
                value={correctedPriority ?? ""}
                onChange={(e) => setCorrectedPriority(e.target.value as "HIGH" | "MEDIUM" | "LOW")}
                className="mt-1.5 w-full rounded-xl border border-brand-200 bg-white px-2 py-2 text-sm outline-none focus:border-brand-400"
              >
                <option value="">Keep AI</option>
                <option>HIGH</option>
                <option>MEDIUM</option>
                <option>LOW</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                Rule
              </label>
              <input
                value={correctedRule}
                onChange={(e) => setCorrectedRule(e.target.value)}
                placeholder="e.g. Energy Isolation"
                className="mt-1.5 w-full rounded-xl border border-brand-200 bg-white px-2 py-2 text-sm outline-none focus:border-brand-400"
              />
            </div>
          </div>

          <label className="mt-4 block text-xs font-bold uppercase tracking-wider text-ink-muted">
            Comment
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            placeholder="Add a review comment…"
            className="mt-1.5 w-full resize-y rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-400"
          />

          <button
            onClick={submitReview}
            disabled={busy || (!decision && !correctedPriority && !correctedRule && !comment)}
            className="btn-primary mt-4 w-full justify-center disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />}
            {report.review_status === "pending" ? "Submit Review" : "Update Review"}
          </button>
          <p className="mt-2 flex items-center gap-1.5 text-[11px] text-ink-muted">
            <MessageSquare size={11} /> Review decisions are stored and can be
            used for model evaluation.
          </p>
        </div>
      </div>
    </div>
  );
}

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-100 bg-white/80 px-2.5 py-1 text-[11px] font-medium text-ink-soft">
      <b className="text-[9px] font-bold uppercase tracking-wider text-ink-muted">
        {label}
      </b>
      {value}
    </span>
  );
}