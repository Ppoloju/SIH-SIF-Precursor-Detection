"use client";

import React, { Fragment, useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  FlaskConical,
  Info,
  Languages,
  Layers,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sliders,
  Sparkles,
  Target,
  XCircle,
} from "lucide-react";
import type {
  CrossValidation,
  EvaluationReport,
  MLModelEvaluationResult,
  MLModelResult,
  RuleMetric,
} from "@/lib/api";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";

const LANG_LABELS: Record<string, string> = {
  en: "English",
  hi: "Hindi (Devanagari)",
  "hi-latn": "Hindi (roman)",
  bn: "Bengali",
  "bn-latn": "Bengali (roman)",
  as: "Assamese",
  "as-latn": "Assamese (roman)",
};

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  tone = "brand",
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  tone?: "brand" | "green" | "amber";
}) {
  const tones = {
    brand: "bg-brand-600",
    green: "bg-green-600",
    amber: "bg-amber-500",
  };
  return (
    <div className="card">
      <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
        <span className={`grid h-6 w-6 place-items-center rounded-lg text-white ${tones[tone]}`}>
          <Icon size={13} />
        </span>
        {label}
      </div>
      <div className="mt-2 text-3xl font-extrabold tracking-tight text-ink">{value}</div>
      {sub && <div className="mt-1 text-xs text-ink-muted">{sub}</div>}
    </div>
  );
}

function CvSummary({ cv }: { cv: CrossValidation }) {
  const a = cv.aggregate;
  return (
    <div className="mt-3 rounded-xl border border-brand-100 bg-brand-50/40 p-3.5">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
        {(
          [
            ["F1", a.f1],
            ["Precision", a.precision],
            ["Recall", a.recall],
            ["Accuracy", a.accuracy],
          ] as const
        ).map(([label, m]) => (
          <span key={label} className="text-xs text-ink-soft">
            <b className="text-ink">{label}</b>{" "}
            <span className="font-mono font-bold text-brand-700">
              {m.mean.toFixed(3)} ± {m.std.toFixed(3)}
            </span>{" "}
            <span className="text-[10.5px] text-ink-muted">
              (range {m.min.toFixed(3)}–{m.max.toFixed(3)}, 95% CI [
              {m.ci95_low.toFixed(3)}, {m.ci95_high.toFixed(3)}])
            </span>
          </span>
        ))}
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-ink-muted">
        {cv.methodology}
      </p>
    </div>
  );
}

function RuleRow({ m, maxF1 }: { m: RuleMetric; maxF1: number }) {
  return (
    <div className="grid grid-cols-[1.4fr_repeat(3,0.7fr)_0.9fr] items-center gap-2 border-b border-brand-50 py-2 text-sm last:border-0">
      <span className="font-semibold text-ink-soft">{m.rule}</span>
      <span className="font-mono text-xs text-ink-muted">{m.tp}/{m.support} hits</span>
      <span className="font-mono text-xs">{pct(m.precision)}</span>
      <span className="font-mono text-xs">{pct(m.recall)}</span>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-brand-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
            style={{ width: `${(m.f1 / maxF1) * 100}%` }}
          />
        </div>
        <span className="w-9 font-mono text-xs font-bold text-brand-700">
          {m.f1.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

function MlModelEvaluationSection({
  data,
  onRerun,
  running,
}: {
  data: MLModelEvaluationResult;
  onRerun: () => void;
  running: boolean;
}) {
  const [expandedModel, setExpandedModel] = useState<string | null>(
    data.recommended_model?.model || null
  );

  return (
    <div className="mt-8 rounded-2xl border border-brand-200 bg-white p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-brand-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-white">
              <Cpu size={16} />
            </span>
            <h2 className="text-lg font-bold text-ink">
              Stratified 5-Fold Cross-Validation Engine
            </h2>
            <span className="rounded-full bg-brand-100 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-brand-700">
              Evidence &amp; Validation Tab
            </span>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            Evaluates classifier generalizability over {data.total_records} safety reports ({data.sif_positive_records} SIF Potential / {data.non_sif_records} Non-SIF). Vectorizer fitted inside pipelines to prevent data leakage.
          </p>
        </div>
        <button
          onClick={onRerun}
          disabled={running}
          className="btn-primary py-1.5 text-xs"
        >
          <RefreshCw size={13} className={running ? "animate-spin" : ""} />
          {running ? "Running 5-Fold Validation..." : "Re-Run 5-Fold Validation"}
        </button>
      </div>

      {/* Dataset Summary Cards */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-brand-100 bg-brand-50/50 p-3">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-ink-muted">
            Validation Method
          </div>
          <div className="mt-1 font-semibold text-ink text-sm">
            {data.evaluation_method}
          </div>
          <div className="mt-0.5 text-[11px] text-ink-muted">
            {data.n_splits} folds · Shuffle = True
          </div>
        </div>

        <div className="rounded-xl border border-brand-100 bg-brand-50/50 p-3">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-ink-muted">
            Dataset Size &amp; Balance
          </div>
          <div className="mt-1 font-semibold text-ink text-sm">
            {data.total_records} Reports
          </div>
          <div className="mt-0.5 text-[11px] text-ink-muted">
            {data.sif_positive_records} SIF ({Math.round(100 * data.sif_positive_records / data.total_records)}%) · {data.non_sif_records} Non-SIF
          </div>
        </div>

        <div className="rounded-xl border border-green-200 bg-green-50/60 p-3">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-green-800">
            Recommended Model
          </div>
          <div className="mt-1 font-extrabold text-green-900 text-sm flex items-center gap-1.5">
            <Sparkles size={14} className="text-amber-500" />
            {data.recommended_model.model}
          </div>
          <div className="mt-0.5 font-mono text-[11px] font-bold text-green-800">
            F2: {data.recommended_model.f2_mean.toFixed(3)} · Recall: {pct(data.recommended_model.recall_mean)}
          </div>
        </div>

        <div className="rounded-xl border border-brand-100 bg-brand-50/50 p-3">
          <div className="text-[10.5px] font-bold uppercase tracking-wider text-ink-muted">
            Selection Metric
          </div>
          <div className="mt-1 font-semibold text-ink text-sm">
            Highest F2 Score &amp; SIF Recall
          </div>
          <div className="mt-0.5 text-[11px] text-ink-muted">
            Safety-first metric weighting
          </div>
        </div>
      </div>

      {/* Model Comparison Table */}
      <div className="mt-5">
        <h3 className="text-sm font-bold text-ink flex items-center gap-2">
          <BarChart3 size={15} className="text-brand-600" />
          Model Cross-Validation Metrics Comparison
        </h3>
        <div className="mt-2 overflow-x-auto rounded-xl border border-brand-100">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-brand-100 bg-brand-50/80 font-bold uppercase tracking-wider text-ink-muted">
                <th className="px-3 py-2.5">Model</th>
                <th className="px-3 py-2.5">Precision (Mean ± Std)</th>
                <th className="px-3 py-2.5">Recall (Mean ± Std)</th>
                <th className="px-3 py-2.5">F1 Score (Mean ± Std)</th>
                <th className="px-3 py-2.5">F2 Score (Weighted)</th>
                <th className="px-3 py-2.5">Accuracy</th>
                <th className="px-3 py-2.5 text-right">Folds Process</th>
              </tr>
            </thead>
            <tbody>
              {data.models.map((m) => {
                const isBest = m.model === data.recommended_model.model;
                const isExpanded = expandedModel === m.model;
                return (
                  <Fragment key={m.model}>
                    <tr
                      className={`border-b border-brand-50 transition-colors ${
                        isBest ? "bg-green-50/40 font-semibold" : "hover:bg-brand-50/30"
                      }`}
                    >
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink">{m.model}</span>
                          {isBest && (
                            <span className="rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                              Recommended
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-mono">
                        {m.precision_mean.toFixed(3)} ± {m.precision_std.toFixed(3)}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-brand-700 font-bold">
                        {m.recall_mean.toFixed(3)} ± {m.recall_std.toFixed(3)}
                      </td>
                      <td className="px-3 py-2.5 font-mono">
                        {m.f1_mean.toFixed(3)} ± {m.f1_std.toFixed(3)}
                      </td>
                      <td className="px-3 py-2.5 font-mono font-extrabold text-brand-800">
                        {m.f2_mean.toFixed(3)} ± {m.f2_std.toFixed(3)}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-ink-muted">
                        {m.accuracy_mean.toFixed(3)}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <button
                          onClick={() => setExpandedModel(isExpanded ? null : m.model)}
                          className="inline-flex items-center gap-1 rounded-lg border border-brand-200 bg-white px-2.5 py-1 text-[11px] font-medium text-brand-700 hover:bg-brand-50"
                        >
                          {isExpanded ? (
                            <>
                              Hide Folds <ChevronUp size={12} />
                            </>
                          ) : (
                            <>
                              View Folds <ChevronDown size={12} />
                            </>
                          )}
                        </button>
                      </td>
                    </tr>

                    {/* Per-Fold Process Breakdown */}
                    {isExpanded && (
                      <tr className="bg-brand-50/20">
                        <td colSpan={7} className="px-4 py-3 border-b border-brand-100">
                          <div className="rounded-lg border border-brand-100 bg-white p-3">
                            <h4 className="text-xs font-bold text-brand-700 flex items-center gap-1.5 mb-2">
                              <Layers size={13} />
                              {m.model} — Stratified 5-Fold Validation Process Breakdown
                            </h4>
                            <table className="w-full text-left text-[11px]">
                              <thead>
                                <tr className="border-b border-brand-100 text-ink-muted font-semibold uppercase">
                                  <th className="py-1">Fold</th>
                                  <th className="py-1">Test Size</th>
                                  <th className="py-1">Confusion Matrix (TP / FP / FN / TN)</th>
                                  <th className="py-1">Precision</th>
                                  <th className="py-1">Recall</th>
                                  <th className="py-1">F1</th>
                                  <th className="py-1 font-bold text-brand-700">F2 Score</th>
                                  <th className="py-1">Accuracy</th>
                                </tr>
                              </thead>
                              <tbody>
                                {m.folds.map((f) => (
                                  <tr key={f.fold} className="border-b border-brand-50 last:border-0">
                                    <td className="py-1.5 font-mono font-bold text-brand-700">
                                      Fold {f.fold}
                                    </td>
                                    <td className="py-1.5 text-ink-muted">{f.n_test} reports</td>
                                    <td className="py-1.5 font-mono text-ink-soft">
                                      TP:{f.tp} | FP:{f.fp} | FN:{f.fn} | TN:{f.tn}
                                    </td>
                                    <td className="py-1.5 font-mono">{pct(f.precision)}</td>
                                    <td className="py-1.5 font-mono font-semibold text-brand-700">{pct(f.recall)}</td>
                                    <td className="py-1.5 font-mono">{f.f1.toFixed(3)}</td>
                                    <td className="py-1.5 font-mono font-bold text-brand-800">{f.f2.toFixed(3)}</td>
                                    <td className="py-1.5 font-mono text-ink-muted">{pct(f.accuracy)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Threshold Analysis Section */}
      {data.threshold_analysis && data.threshold_analysis.length > 0 && (
        <div className="mt-6 rounded-xl border border-brand-100 bg-brand-50/30 p-4">
          <h3 className="text-xs font-bold text-ink flex items-center gap-1.5">
            <Sliders size={14} className="text-brand-600" />
            Decision Threshold Sensitivity Analysis (Logistic Regression)
          </h3>
          <p className="mt-1 text-[11.5px] text-ink-muted">
            Tuning probability threshold cutoffs balances SIF Recall (catching hazards) against Precision (HSE review workload).
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-4">
            {data.threshold_analysis.map((t) => (
              <div
                key={t.threshold}
                className={`rounded-lg border p-2.5 bg-white ${
                  t.threshold === 0.40 ? "border-brand-300 ring-1 ring-brand-400" : "border-brand-100"
                }`}
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-brand-700">Threshold ≥ {t.threshold.toFixed(2)}</span>
                  {t.threshold === 0.40 && (
                    <span className="rounded bg-brand-100 px-1.5 py-0.5 text-[9.5px] font-bold text-brand-800">
                      Optimal
                    </span>
                  )}
                </div>
                <div className="mt-2 space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Recall:</span>
                    <span className="font-bold text-brand-700">{pct(t.recall)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Precision:</span>
                    <span>{pct(t.precision)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">F2 Score:</span>
                    <span className="font-bold">{t.f2.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between text-[10px] text-ink-muted border-t pt-1 mt-1">
                    <span>Flagged for review:</span>
                    <span>{t.reports_flagged_sif}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Explanations & Limitations */}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-brand-100 bg-brand-50/40 p-3.5 text-xs text-ink-soft">
          <h4 className="font-bold text-brand-700 flex items-center gap-1.5 mb-1.5">
            <Info size={14} />
            Why Prioritize F2 Score over F1 / Precision?
          </h4>
          <p className="leading-relaxed text-[11.5px]">
            In Serious Injury &amp; Fatality (SIF) precursor detection, <b>missing a genuine life-threatening hazard (False Negative)</b> has catastrophic consequences. F2 score assigns 4x weight to Recall over Precision. Thus, a model that catches 94%+ of SIF precursors is vastly superior for safety deployment, even if it requires inspecting a few extra reports.
          </p>
        </div>

        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3.5 text-xs text-amber-900">
          <h4 className="font-bold text-amber-800 flex items-center gap-1.5 mb-1.5">
            <ShieldAlert size={14} />
            Validation Evidence &amp; Deployment Limitations
          </h4>
          <ul className="space-y-1 text-[11px] leading-relaxed text-amber-950">
            {data.limitations.map((lim, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-amber-600 font-bold">•</span>
                <span>{lim}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function EvaluationPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [mlCvData, setMlCvData] = useState<MLModelEvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningMlCv, setRunningMlCv] = useState(false);

  function load(fresh = false) {
    setLoading(true);
    setError(null);
    api
      .getEvaluation(fresh)
      .then((data) => {
        setReport(data);
        if (data.ml_cross_validation) {
          setMlCvData(data.ml_cross_validation);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Evaluation failed"))
      .finally(() => setLoading(false));
  }

  function runMlEvaluation() {
    setRunningMlCv(true);
    api
      .evaluateModel()
      .then((res) => {
        if (res.success && res.data) {
          setMlCvData(res.data);
        } else {
          setError(res.error || "ML Cross-validation failed");
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "ML evaluation failed"))
      .finally(() => setRunningMlCv(false));
  }

  useEffect(() => {
    load();
  }, []);

  if (loading && !report) {
    return (
      <div className="grid place-items-center py-32">
        <Loader2 className="animate-spin text-brand-500" size={26} />
      </div>
    );
  }

  const s = report?.sif_classification;
  const maxF1 = Math.max(0.01, ...(report?.rules ?? []).map((r) => r.f1));
  const issues = (report?.cases ?? []).filter((c) => !c.sif_match || !c.rule_match);
  const perfect = issues.length === 0;
  const okCount = (report?.cases ?? []).length;

  return (
    <div className="mx-auto max-w-5xl animate-rise">
      <PageHeader
        kicker="Model Evaluation &amp; Cross-Validation"
        title="Model Evaluation &amp; Stratified 5-Fold Validation"
        icon={FlaskConical}
        lede="Rigorous evaluation evidence page for judges and HSE engineering: compares Multinomial Naive Bayes, Logistic Regression, Linear SVM, and deterministic engine baselines using Stratified 5-Fold Cross-Validation."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={runMlEvaluation}
              disabled={runningMlCv}
              className="btn-primary text-xs"
            >
              <Cpu size={14} className={runningMlCv ? "animate-spin" : ""} />
              {runningMlCv ? "Running 5-Fold ML CV..." : "Run 5-Fold ML Validation"}
            </button>
            <button
              onClick={() => load(true)}
              disabled={loading}
              className="btn-ghost text-xs"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Re-run engine harness
            </button>
          </div>
        }
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ML Stratified 5-Fold Cross-Validation Section */}
      {mlCvData && (
        <MlModelEvaluationSection
          data={mlCvData}
          onRerun={runMlEvaluation}
          running={runningMlCv}
        />
      )}

      {report && s && (
        <>
          <div className="mt-8 border-t border-brand-200 pt-6">
            <h2 className="text-base font-bold text-ink flex items-center gap-2 mb-3">
              <FlaskConical size={18} className="text-brand-600" />
              Deterministic Golden-Set Engine Benchmark (35 Multi-lingual Cases)
            </h2>
          </div>

          {/* Headline metrics */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <MetricCard icon={Target} label="SIF F1 score" value={s.f1.toFixed(3)} sub="harmonic mean of precision & recall" />
            <MetricCard icon={Activity} label="Precision" value={pct(s.precision)} sub={`${s.tp} true positives, ${s.fp} false positives`} tone="green" />
            <MetricCard icon={CheckCircle2} label="Recall" value={pct(s.recall)} sub={`${s.tn} true negatives, ${s.fn} false negatives`} />
            <MetricCard icon={BarChart3} label="Accuracy" value={pct(s.accuracy)} sub={`${okCount} of ${okCount} reference reports correct`} tone="green" />
            <MetricCard
              icon={Languages}
              label="Multilingual"
              value={report.multilingual.sif_accuracy != null ? `${report.multilingual.sif_accuracy}%` : "—"}
              sub={`${report.multilingual.cases} Hindi / Bengali / Assamese reports`}
              tone="amber"
            />
          </div>

          {/* Verdict strip */}
          <div
            className={`mt-4 flex flex-wrap items-center gap-3 rounded-2xl border px-4 py-3 ${
              perfect
                ? "border-green-200 bg-green-50 text-green-800"
                : "border-amber-300 bg-white text-amber-800"
            }`}
          >
            {perfect ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
            <p className="text-sm">
              <b>
                {perfect
                  ? "Every golden reference case detected correctly — 0 false positives, 0 false negatives."
                  : `${issues.length} reference case(s) need attention.`}
              </b>{" "}
              SIF verdicts match on {okCount - issues.filter((c) => !c.sif_match).length}/{okCount} cases; rule
              sets match exactly on {okCount - issues.filter((c) => !c.rule_match).length}/{okCount} cases.
            </p>
            <span className="ml-auto rounded-full bg-white/80 px-3 py-1 font-mono text-[11px]">
              {report.runtime_ms} ms · {report.generated_at}
            </span>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            {/* SIF confusion */}
            <div className="card">
              <h2 className="card-title text-brand-600">SIF classification — confusion</h2>
              <div className="mt-3 grid grid-cols-2 gap-2 text-center">
                {[
                  { label: "True positive", v: s.tp, cls: "border-green-200 bg-green-50 text-green-700" },
                  { label: "True negative", v: s.tn, cls: "border-brand-100 bg-brand-50 text-brand-700" },
                  { label: "False positive", v: s.fp, cls: "border-orange-200 bg-orange-50 text-orange-700" },
                  { label: "False negative", v: s.fn, cls: "border-red-200 bg-red-50 text-red-700" },
                ].map((c) => (
                  <div key={c.label} className={`rounded-xl border p-3 ${c.cls}`}>
                    <div className="text-2xl font-extrabold">{c.v}</div>
                    <div className="mt-0.5 text-[10.5px] font-bold uppercase tracking-wide opacity-80">
                      {c.label}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs leading-relaxed text-ink-muted">
                A true positive is a report labeled SIF-potential that the engine
                flagged; a false negative is one it missed. The demo reference set
                is deliberately exact, so these numbers describe the deterministic
                rules — not statistical generalization.
              </p>
            </div>

            {/* Language coverage */}
            <div className="card">
              <h2 className="card-title text-brand-600">Language coverage</h2>
              <ul className="mt-3 space-y-2">
                {report.languages.map((l) => (
                  <li key={l.lang} className="flex items-center gap-3 text-sm">
                    <span className="w-40 truncate font-semibold text-ink-soft">
                      {LANG_LABELS[l.lang] ?? l.lang}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-brand-100">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                        style={{ width: `${l.sif_accuracy}%` }}
                      />
                    </div>
                    <span className="w-24 text-right font-mono text-xs text-ink-muted">
                      {l.sif_correct}/{l.cases} · {l.sif_accuracy}%
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-ink-muted">
                OIL reports mix English with Hindi, Assamese and Bengali — the
                engine detects those scripts/phrases and maps them to the same
                Life-Saving Rules.
              </p>
            </div>
          </div>

          {/* Stratified k-fold stability check */}
          {report.cross_validation && (
            <div className="card mt-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="card-title text-brand-600">
                  Golden Set Stratified {report.cross_validation.k}-Fold Stability Check
                </h2>
                <span className="text-[11px] text-ink-muted">
                  {report.cross_validation.n_cases} golden cases · folds mirror
                  the SIF &amp; language mix
                </span>
              </div>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-xs">
                  <thead>
                    <tr className="border-b border-brand-100 uppercase tracking-wider text-ink-muted">
                      <th className="px-2 py-1.5">Fold</th>
                      <th className="px-2 py-1.5">Cases</th>
                      <th className="px-2 py-1.5">SIF+</th>
                      <th className="px-2 py-1.5">Precision</th>
                      <th className="px-2 py-1.5">Recall</th>
                      <th className="px-2 py-1.5">F1</th>
                      <th className="px-2 py-1.5">Accuracy</th>
                      <th className="px-2 py-1.5">Composition (lang × n)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.cross_validation.folds.map((f) => (
                      <tr
                        key={f.fold}
                        className="border-b border-brand-50 last:border-0"
                      >
                        <td className="px-2 py-1.5 font-mono font-bold text-brand-700">
                          {f.fold}
                        </td>
                        <td className="px-2 py-1.5">{f.n}</td>
                        <td className="px-2 py-1.5">{f.sif_positive}</td>
                        <td className="px-2 py-1.5 font-mono">
                          {pct(f.precision)}
                        </td>
                        <td className="px-2 py-1.5 font-mono">
                          {pct(f.recall)}
                        </td>
                        <td className="px-2 py-1.5 font-mono font-bold text-brand-700">
                          {f.f1.toFixed(3)}
                        </td>
                        <td className="px-2 py-1.5 font-mono">
                          {pct(f.accuracy)}
                        </td>
                        <td className="px-2 py-1.5 text-[10.5px] text-ink-muted">
                          {f.languages}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <CvSummary cv={report.cross_validation} />
            </div>
          )}

          {/* Per-rule table */}
          <div className="card mt-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="card-title text-brand-600">
                Life-Saving-Rule mapping — per-rule metrics
              </h2>
              <span className="text-[11px] text-ink-muted">
                multi-label · support = reference cases for that rule
              </span>
            </div>
            <div className="mt-3 grid grid-cols-[1.4fr_repeat(3,0.7fr)_0.9fr] gap-2 border-b border-brand-100 pb-2 text-[10.5px] font-bold uppercase tracking-wider text-ink-muted">
              <span>Rule</span>
              <span>Hits</span>
              <span>Precision</span>
              <span>Recall</span>
              <span>F1</span>
            </div>
            {report.rules.map((m) => (
              <RuleRow key={m.rule} m={m} maxF1={maxF1} />
            ))}
          </div>

          {/* Methodology */}
          <div className="mt-4 rounded-xl border border-brand-100 bg-brand-50/50 p-4 text-xs leading-relaxed text-ink-soft">
            <b className="text-brand-700">Methodology · </b>
            {report.methodology} The golden set ({report.dataset.name}, {report.dataset.total} cases)
            lives in the repository and is used by the CLI (<code className="font-mono">python scripts/evaluate.py</code>)
            and this page.
          </div>
        </>
      )}
    </div>
  );
}
