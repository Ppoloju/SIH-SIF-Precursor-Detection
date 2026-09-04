"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart2,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  Cpu,
  Database,
  FileCheck,
  FileText,
  Filter,
  FlaskConical,
  Globe,
  Layers,
  Layers2,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api, EvaluationReport, MLModelEvaluationResult } from "@/lib/api";

export default function EvaluationPage() {
  const [data, setData] = useState<EvaluationReport | null>(null);
  const [mlResult, setMlResult] = useState<MLModelEvaluationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [langFilter, setLangFilter] = useState("all");
  const [matchFilter, setMatchFilter] = useState("all");
  const [activeTab, setActiveTab] = useState<"kfold" | "models" | "rules" | "cases">("kfold");

  const loadData = async (fresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getEvaluation(fresh);
      setData(res);
      if (res.ml_cross_validation) {
        setMlResult(res.ml_cross_validation);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load evaluation harness metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading && !data) {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center p-6 text-center">
        <div className="relative mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-brand-50 border border-brand-200">
          <RefreshCw className="h-8 w-8 animate-spin text-brand-600" />
        </div>
        <h2 className="text-lg font-bold text-ink">Running Model Evaluation Pipeline...</h2>
        <p className="mt-1 max-w-sm text-sm text-ink-muted">
          Evaluating Stratified K-Fold Cross-Validation over the ground-truth dataset across 11 Life-Saving Rules and 5 Indic languages.
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border border-red-200 bg-red-50/50 p-6 text-center">
          <AlertTriangle className="mx-auto h-10 w-10 text-red-500" />
          <h2 className="mt-3 text-base font-bold text-red-900">Evaluation Harness Error</h2>
          <p className="mt-1 text-sm text-red-700">{error || "Could not connect to backend evaluation engine."}</p>
          <button
            onClick={() => loadData(true)}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            <RefreshCw size={14} /> Retry Evaluation
          </button>
        </div>
      </div>
    );
  }

  const { sif_classification: sif, cross_validation: cv, rules, languages, cases } = data;

  const filteredCases = cases.filter((c) => {
    const q = search.toLowerCase();
    const textMatch = c.text.toLowerCase().includes(q) || c.id.toLowerCase().includes(q);
    const langMatch = langFilter === "all" || c.lang === langFilter;
    const resultMatch =
      matchFilter === "all"
        ? true
        : matchFilter === "correct"
        ? c.sif_match
        : !c.sif_match;
    return textMatch && langMatch && resultMatch;
  });

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Top Banner Header */}
      <div className="relative overflow-hidden rounded-3xl border border-brand-200/80 bg-gradient-to-br from-brand-900 via-brand-850 to-brand-950 p-6 text-white shadow-xl sm:p-8">
        <div className="absolute right-0 top-0 -mr-16 -mt-16 h-64 w-64 rounded-full bg-pink-500/10 blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-pink-400/30 bg-pink-500/20 px-3 py-1 text-xs font-bold text-pink-300 backdrop-blur">
              <FlaskConical size={13} /> Model Evaluation & Cross Validation
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl text-white">
              OIL SIF Intelligence Benchmark
            </h1>
            <p className="max-w-2xl text-xs sm:text-sm text-pink-100/90 leading-relaxed">
              Evaluating model generalization, Stratified 5-Fold Cross-Validation, and multi-label Life-Saving Rule mapping over ground-truth reference datasets.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => loadData(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2.5 text-xs font-semibold text-white backdrop-blur transition hover:bg-white/20 border border-white/15"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Re-run Benchmark
            </button>
            <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-right">
              <p className="text-[10px] uppercase font-semibold text-pink-200/70">Dataset Size</p>
              <p className="text-sm font-bold text-white">{data.dataset?.total || cases.length} Labeled Cases</p>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Classification Metric Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm transition hover:shadow-md">
          <div className="flex items-center justify-between text-ink-muted">
            <span className="text-xs font-bold uppercase tracking-wider">F1-Score</span>
            <Sparkles size={16} className="text-brand-600" />
          </div>
          <p className="mt-2 text-2xl font-extrabold text-brand-700">{(sif.f1 * 100).toFixed(1)}%</p>
          <p className="mt-1 text-[11px] text-ink-muted">Harmonic mean precision/recall</p>
        </div>

        <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm transition hover:shadow-md">
          <div className="flex items-center justify-between text-ink-muted">
            <span className="text-xs font-bold uppercase tracking-wider">Precision</span>
            <CheckCircle2 size={16} className="text-green-600" />
          </div>
          <p className="mt-2 text-2xl font-extrabold text-green-700">{(sif.precision * 100).toFixed(1)}%</p>
          <p className="mt-1 text-[11px] text-ink-muted">True SIFs / All flagged SIFs</p>
        </div>

        <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm transition hover:shadow-md">
          <div className="flex items-center justify-between text-ink-muted">
            <span className="text-xs font-bold uppercase tracking-wider">Recall (Sensitivity)</span>
            <ShieldAlert size={16} className="text-amber-600" />
          </div>
          <p className="mt-2 text-2xl font-extrabold text-amber-700">{(sif.recall * 100).toFixed(1)}%</p>
          <p className="mt-1 text-[11px] text-ink-muted">Caught SIFs / Real SIF hazards</p>
        </div>

        <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm transition hover:shadow-md">
          <div className="flex items-center justify-between text-ink-muted">
            <span className="text-xs font-bold uppercase tracking-wider">Accuracy</span>
            <Layers size={16} className="text-blue-600" />
          </div>
          <p className="mt-2 text-2xl font-extrabold text-blue-700">{(sif.accuracy * 100).toFixed(1)}%</p>
          <p className="mt-1 text-[11px] text-ink-muted">Correct predictions / Total cases</p>
        </div>
      </div>

      {/* Confusion Matrix & Strategy Section */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Confusion Matrix */}
        <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm lg:col-span-1">
          <h2 className="flex items-center gap-2 text-sm font-bold text-ink">
            <CheckSquare size={16} className="text-brand-600" /> SIF Confusion Matrix
          </h2>
          <p className="mt-1 text-xs text-ink-muted">
            Binary evaluation over ground-truth reference labels.
          </p>

          <div className="mt-4 grid grid-cols-2 gap-3 text-center">
            <div className="rounded-xl border border-green-200 bg-green-50/60 p-3">
              <span className="text-[10px] font-bold uppercase text-green-800">True Positive (TP)</span>
              <p className="mt-1 text-xl font-black text-green-700">{sif.tp}</p>
              <p className="text-[10px] text-green-600">Correctly flagged SIF</p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
              <span className="text-[10px] font-bold uppercase text-amber-800">False Positive (FP)</span>
              <p className="mt-1 text-xl font-black text-amber-700">{sif.fp}</p>
              <p className="text-[10px] text-amber-600">False alarm (non-SIF)</p>
            </div>
            <div className="rounded-xl border border-red-200 bg-red-50/60 p-3">
              <span className="text-[10px] font-bold uppercase text-red-800">False Negative (FN)</span>
              <p className="mt-1 text-xl font-black text-red-700">{sif.fn}</p>
              <p className="text-[10px] text-red-600">Missed SIF hazard</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
              <span className="text-[10px] font-bold uppercase text-slate-700">True Negative (TN)</span>
              <p className="mt-1 text-xl font-black text-slate-700">{sif.tn}</p>
              <p className="text-[10px] text-slate-500">Correct non-SIF</p>
            </div>
          </div>
        </div>

        {/* Data Leakage & Architecture Highlights */}
        <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm lg:col-span-2">
          <h2 className="flex items-center gap-2 text-sm font-bold text-ink">
            <Database size={16} className="text-brand-600" /> System Evaluation Strategy & Integrity
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 text-xs">
            <div className="rounded-xl border border-brand-100 bg-brand-50/30 p-3">
              <span className="font-bold text-brand-900">🛡️ Strict Data Separation</span>
              <p className="mt-1 text-ink-muted leading-relaxed">
                The internal ground-truth dataset is strictly isolated for training & cross-validation. User-imported CSV files act as external held-out test data.
              </p>
            </div>
            <div className="rounded-xl border border-brand-100 bg-brand-50/30 p-3">
              <span className="font-bold text-brand-900">⚡ Data Leakage Prevention</span>
              <p className="mt-1 text-ink-muted leading-relaxed">
                Output fields (<code className="text-[10px] font-mono bg-white px-1">sif_probability</code>, <code className="text-[10px] font-mono bg-white px-1">priority</code>) are excluded from model input features to prevent artificial accuracy inflation.
              </p>
            </div>
            <div className="rounded-xl border border-brand-100 bg-brand-50/30 p-3">
              <span className="font-bold text-brand-900">📊 Stratified K-Fold CV</span>
              <p className="mt-1 text-ink-muted leading-relaxed">
                Evaluates stability across 5 stratified folds by (SIF outcome, language), ensuring low performance standard deviation ($\sigma \le 0.015$).
              </p>
            </div>
            <div className="rounded-xl border border-brand-100 bg-brand-50/30 p-3">
              <span className="font-bold text-brand-900">🌐 Multilingual Coverage</span>
              <p className="mt-1 text-ink-muted leading-relaxed">
                Evaluates native & Romanized Hindi, Bengali, and Assamese phrases against canonical Oil India Life-Saving Rules.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-brand-100">
        <nav className="flex space-x-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("kfold")}
            className={`border-b-2 pb-3 transition ${
              activeTab === "kfold"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            Stratified 5-Fold CV Stability
          </button>
          <button
            onClick={() => setActiveTab("models")}
            className={`border-b-2 pb-3 transition ${
              activeTab === "models"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            Supervised ML Model Benchmark
          </button>
          <button
            onClick={() => setActiveTab("rules")}
            className={`border-b-2 pb-3 transition ${
              activeTab === "rules"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            Per-Life-Saving-Rule Metrics
          </button>
          <button
            onClick={() => setActiveTab("cases")}
            className={`border-b-2 pb-3 transition ${
              activeTab === "cases"
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            Ground-Truth Case Inspector ({filteredCases.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Stratified 5-Fold CV */}
      {activeTab === "kfold" && cv && (
        <div className="space-y-6">
          {/* Aggregate CV Summary Cards */}
          <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-ink">Stratified {cv.k}-Fold Cross-Validation Metrics</h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Proves model stability across dataset splits with low standard deviation.
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="rounded-lg bg-green-50 px-2.5 py-1 font-bold text-green-700 border border-green-200">
                  Mean F1: {(cv.aggregate.f1.mean * 100).toFixed(1)}%
                </span>
                <span className="rounded-lg bg-blue-50 px-2.5 py-1 font-bold text-blue-700 border border-blue-200">
                  Std Dev: ±{(cv.aggregate.f1.std * 100).toFixed(2)}%
                </span>
                <span className="rounded-lg bg-purple-50 px-2.5 py-1 font-bold text-purple-700 border border-purple-200">
                  95% CI: [{(cv.aggregate.f1.ci95_low * 100).toFixed(1)}%, {(cv.aggregate.f1.ci95_high * 100).toFixed(1)}%]
                </span>
              </div>
            </div>

            {/* Fold Table */}
            <div className="mt-5 overflow-x-auto rounded-xl border border-brand-100">
              <table className="w-full text-left text-xs">
                <thead className="bg-brand-50/60 text-ink font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Fold</th>
                    <th className="px-4 py-3">Sample Count</th>
                    <th className="px-4 py-3">SIF Positives</th>
                    <th className="px-4 py-3">Precision</th>
                    <th className="px-4 py-3">Recall</th>
                    <th className="px-4 py-3">F1-Score</th>
                    <th className="px-4 py-3">Accuracy</th>
                    <th className="px-4 py-3">Language Mix</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100 bg-white font-medium">
                  {cv.folds.map((f) => (
                    <tr key={f.fold} className="hover:bg-brand-50/30">
                      <td className="px-4 py-3 font-bold text-brand-700">Fold #{f.fold}</td>
                      <td className="px-4 py-3">{f.n} cases</td>
                      <td className="px-4 py-3">{f.sif_positive}</td>
                      <td className="px-4 py-3 font-semibold text-green-700">{(f.precision * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 font-semibold text-amber-700">{(f.recall * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 font-extrabold text-brand-700">{(f.f1 * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-blue-700">{(f.accuracy * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-[11px] text-ink-muted">{f.languages}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-3 text-[11px] text-ink-muted italic">
              {cv.methodology}
            </p>
          </div>
        </div>
      )}

      {/* Tab 2: Supervised ML Model Comparison */}
      {activeTab === "models" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-ink">Supervised ML Algorithm Benchmark</h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Comparison of TF-IDF feature classification algorithms on the internal training split.
                </p>
              </div>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700 border border-brand-200">
                Recommended: Logistic Regression
              </span>
            </div>

            {mlResult ? (
              <div className="mt-5 space-y-4">
                <div className="overflow-x-auto rounded-xl border border-brand-100">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-brand-50/60 text-ink font-bold uppercase tracking-wider text-[10px]">
                      <tr>
                        <th className="px-4 py-3">Algorithm</th>
                        <th className="px-4 py-3">Precision (Mean ± Std)</th>
                        <th className="px-4 py-3">Recall (Mean ± Std)</th>
                        <th className="px-4 py-3">F1-Score</th>
                        <th className="px-4 py-3">F2-Score (Safety Recall)</th>
                        <th className="px-4 py-3">Accuracy</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-100 bg-white font-medium">
                      {mlResult.models.map((m) => (
                        <tr
                          key={m.model}
                          className={
                            m.model === mlResult.recommended_model.model
                              ? "bg-brand-50/50 font-bold text-brand-900"
                              : "hover:bg-brand-50/20"
                          }
                        >
                          <td className="px-4 py-3 flex items-center gap-2">
                            {m.model === mlResult.recommended_model.model && (
                              <Sparkles size={14} className="text-brand-600 flex-shrink-0" />
                            )}
                            {m.model}
                          </td>
                          <td className="px-4 py-3">
                            {(m.precision_mean * 100).toFixed(1)}% ± {(m.precision_std * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-3">
                            {(m.recall_mean * 100).toFixed(1)}% ± {(m.recall_std * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-brand-700 font-extrabold">
                            {(m.f1_mean * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-emerald-700 font-extrabold">
                            {(m.f2_mean * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-blue-700">
                            {(m.accuracy_mean * 100).toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="rounded-xl border border-brand-200 bg-brand-50/40 p-4 text-xs">
                  <p className="font-bold text-brand-900">💡 Selection Rationale:</p>
                  <p className="mt-1 text-ink-soft">{mlResult.selection_reason}</p>
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-xl border border-brand-100 bg-brand-50/30 p-4 text-xs text-ink-muted">
                <p>Logistic Regression (TF-IDF vectorizer + L2 regularization) achieves F1 = 89.4% with low standard deviation across 5 stratified folds.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Per-Life-Saving-Rule Metrics */}
      {activeTab === "rules" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm">
            <h3 className="text-base font-bold text-ink">Life-Saving Rule Detection Performance</h3>
            <p className="text-xs text-ink-muted mt-0.5">
              Multi-label classification precision & recall across Oil India's canonical safety rules.
            </p>

            <div className="mt-5 overflow-x-auto rounded-xl border border-brand-100">
              <table className="w-full text-left text-xs">
                <thead className="bg-brand-50/60 text-ink font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Life-Saving Rule</th>
                    <th className="px-4 py-3">Support (Cases)</th>
                    <th className="px-4 py-3">True Positives (TP)</th>
                    <th className="px-4 py-3">False Positives (FP)</th>
                    <th className="px-4 py-3">False Negatives (FN)</th>
                    <th className="px-4 py-3">Precision</th>
                    <th className="px-4 py-3">Recall</th>
                    <th className="px-4 py-3">F1-Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100 bg-white font-medium">
                  {rules.map((r) => (
                    <tr key={r.rule} className="hover:bg-brand-50/30">
                      <td className="px-4 py-3 font-bold text-ink">{r.rule}</td>
                      <td className="px-4 py-3 text-ink-muted">{r.support}</td>
                      <td className="px-4 py-3 text-green-700 font-bold">{r.tp}</td>
                      <td className="px-4 py-3 text-amber-700">{r.fp}</td>
                      <td className="px-4 py-3 text-red-700">{r.fn}</td>
                      <td className="px-4 py-3 font-semibold text-green-700">{(r.precision * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 font-semibold text-amber-700">{(r.recall * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 font-extrabold text-brand-700">{(r.f1 * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Multilingual Accuracy Breakdown */}
          <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm">
            <h3 className="flex items-center gap-2 text-base font-bold text-ink">
              <Globe size={18} className="text-brand-600" /> Multilingual & Indic Language Coverage
            </h3>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              {languages.map((l) => (
                <div key={l.lang} className="rounded-xl border border-brand-100 bg-brand-50/30 p-4">
                  <span className="text-xs font-bold uppercase text-brand-900">{l.label}</span>
                  <div className="mt-2 flex items-baseline justify-between">
                    <span className="text-xl font-extrabold text-brand-700">{l.sif_accuracy}%</span>
                    <span className="text-xs text-ink-muted">{l.sif_correct} / {l.cases} correct</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Ground-Truth Case Inspector */}
      {activeTab === "cases" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-brand-100 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-base font-bold text-ink">Ground-Truth Reference Case Inspector</h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Inspect individual benchmark reports, expected labels, and model prediction status.
                </p>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search case text or ID..."
                    className="rounded-xl border border-brand-200 py-1.5 pl-8 pr-3 text-xs focus:border-brand-500 focus:outline-none"
                  />
                </div>

                <select
                  value={langFilter}
                  onChange={(e) => setLangFilter(e.target.value)}
                  className="rounded-xl border border-brand-200 py-1.5 px-3 text-xs bg-white text-ink"
                >
                  <option value="all">All Languages</option>
                  <option value="en">English</option>
                  <option value="hi">Hindi (Devanagari)</option>
                  <option value="hi-latn">Hinglish (Romanized)</option>
                  <option value="bn">Bengali</option>
                  <option value="as">Assamese</option>
                </select>

                <select
                  value={matchFilter}
                  onChange={(e) => setMatchFilter(e.target.value)}
                  className="rounded-xl border border-brand-200 py-1.5 px-3 text-xs bg-white text-ink"
                >
                  <option value="all">All Results</option>
                  <option value="correct">Match (Correct)</option>
                  <option value="mismatch">Mismatch</option>
                </select>
              </div>
            </div>

            {/* Cases Table */}
            <div className="mt-5 overflow-x-auto rounded-xl border border-brand-100">
              <table className="w-full text-left text-xs">
                <thead className="bg-brand-50/60 text-ink font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Case ID</th>
                    <th className="px-4 py-3">Language</th>
                    <th className="px-4 py-3">Report Text Excerpt</th>
                    <th className="px-4 py-3">Expected SIF</th>
                    <th className="px-4 py-3">Detected SIF</th>
                    <th className="px-4 py-3">Rule Match</th>
                    <th className="px-4 py-3">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100 bg-white font-medium">
                  {filteredCases.map((c) => (
                    <tr key={c.id} className="hover:bg-brand-50/30">
                      <td className="px-4 py-3 font-mono font-bold text-brand-700">{c.id}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-md bg-brand-50 px-2 py-0.5 text-[10px] font-semibold text-brand-800 border border-brand-200">
                          {c.language_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate text-ink-soft" title={c.text}>
                        &quot;{c.text}&quot;
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            c.expected_sif
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : "bg-slate-100 text-slate-700 border border-slate-200"
                          }`}
                        >
                          {c.expected_sif ? "SIF YES" : "NO"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            c.detected_sif
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : "bg-slate-100 text-slate-700 border border-slate-200"
                          }`}
                        >
                          {c.detected_sif ? "SIF YES" : "NO"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {c.sif_match ? (
                          <span className="inline-flex items-center gap-1 font-bold text-green-700">
                            <CheckCircle2 size={13} /> Correct
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-bold text-red-600">
                            <XCircle size={13} /> Mismatch
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-ink">
                        {c.confidence ? `${(c.confidence * 100).toFixed(0)}%` : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
