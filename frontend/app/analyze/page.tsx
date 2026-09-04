"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, GitCompare, Loader2, Sparkles } from "lucide-react";
import type { AnalyzeResponse } from "@/lib/api";
import { api } from "@/lib/api";
import AnalysisResultCard from "@/components/AnalysisResultCard";
import PageHeader from "@/components/PageHeader";

const EXAMPLES = [
  {
    label: "Energy isolation",
    text: "During maintenance, the technician started work on a pipeline without properly isolating the energy source.",
  },
  {
    label: "Confined space",
    text: "Two workers entered the storage tank without gas testing and no attendant was posted.",
  },
  {
    label: "Working at height",
    text: "Roof worker was seen working at height without a harness and the scaffold lacked guardrails.",
  },
  {
    label: "Lifting",
    text: "Crane lifted the load beyond its rated capacity; the sling angle was unsafe and no banksman was present.",
  },
  {
    label: "Non-SIF (controlled)",
    text: "The crew isolated and depressurized the pipeline before maintenance began; LOTO was applied and verified.",
  },
  {
    label: "Hindi report 🇮🇳",
    text: "Contractor ne bina gas test ke tank ke andar kaam shuru kar diya aur koi attendant nahi tha.",
  },
  {
    label: "Bengali report 🇧🇩",
    text: "পাইপলাইনের কাজ আইসোলেশন ছাড়াই শুরু হয়েছে, লাইনে প্রেশার ছিল।",
  },
];

export default function AnalyzePage() {
  const [text, setText] = useState("");
  const [reportType, setReportType] = useState("");
  const [site, setSite] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAnalysis(e?: React.FormEvent) {
    e?.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.analyzeReport({
        report_text: text,
        report_type: reportType || undefined,
        site: site || undefined,
        store: true,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        kicker="Report Analysis"
        title="Analyze a Safety Report"
        icon={Sparkles}
        lede="Paste a UA / UC, near-miss or incident report. The AI engine detects SIF potential, extracts evidence, maps the Life-Saving Rule, and assigns an AI-assisted priority — then stores the result for HSE review."
      />

      <form onSubmit={runAnalysis} className="card">
        <label className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          Report text *
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="e.g. During maintenance, the technician started work on a pipeline without properly isolating the energy source."
          className="mt-2 w-full resize-y rounded-xl border border-brand-200 bg-white p-3.5 text-sm text-ink outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
        />

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              Report type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
            >
              <option value="">Not specified</option>
              <option>Unsafe Act</option>
              <option>Unsafe Condition</option>
              <option>Near Miss</option>
              <option>Incident</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              Site / location
            </label>
            <input
              value={site}
              onChange={(e) => setSite(e.target.value)}
              placeholder="e.g. Site B — Processing Plant"
              className="mt-1.5 w-full rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400"
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={!text.trim() || loading}
            className="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {loading ? "Analyzing…" : "Analyze Report"}
          </button>
          {result?.report && (
            <Link
              href={`/reports/${result.report.id}`}
              className="btn-ghost"
            >
              Open full report →
            </Link>
          )}
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
            <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </form>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          Try an example:
        </span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.label}
            onClick={() => {
              setText(ex.text);
              setResult(null);
            }}
            className="rounded-full border border-brand-200 bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-50"
          >
            {ex.label}
          </button>
        ))}
      </div>

      {result && (
        <div className="mt-6 space-y-4">
          <AnalysisResultCard result={result.analysis} />

          {result.stored && result.report && result.report.similar_reports.length > 0 && (
            <div className="card">
              <h2 className="card-title">
                <GitCompare size={16} className="text-brand-600" /> Similar past
                reports
              </h2>
              <p className="mt-1 text-xs text-ink-muted">
                This report is most similar to {result.report.similar_reports.length}{" "}
                historical report(s) — check whether the precursor has appeared
                before.
              </p>
              <ul className="mt-3 space-y-2">
                {result.report.similar_reports.map((sr) => (
                  <li key={sr.report_id}>
                    <Link
                      href={`/reports/${sr.id}`}
                      className="group flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-brand-100 bg-brand-50/40 px-3.5 py-2.5 transition hover:border-brand-300 hover:bg-brand-100/60"
                    >
                      <span className="font-mono text-xs font-bold text-brand-700">
                        {sr.report_id}
                      </span>
                      <span className="badge badge-pink">
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

          {result.stored && result.report && (
            <p className="text-xs text-ink-muted">
              ✓ Stored as{" "}
              <Link href={`/reports/${result.report.id}`} className="font-mono font-semibold text-brand-700 hover:underline">
                {result.report.report_id}
              </Link>{" "}
              — ready for HSE review.
            </p>
          )}
        </div>
      )}
    </div>
  );
}