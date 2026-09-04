"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  FlaskConical,
  Languages,
  Loader2,
  RefreshCw,
  Target,
  XCircle,
} from "lucide-react";
import type { EvaluationReport, RuleMetric } from "@/lib/api";
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

export default function EvaluationPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function load(fresh = false) {
    setLoading(true);
    setError(null);
    api
      .getEvaluation(fresh)
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : "Evaluation failed"))
      .finally(() => setLoading(false));
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
        kicker="Evaluation Harness"
        title="How Well Does the Engine Detect SIF Precursors?"
        icon={FlaskConical}
        lede="The engine is held against a hand-labeled golden set of 35 reports — English, Hindi, Bengali and Assamese — measuring SIF classification and Life-Saving-Rule mapping. Deterministic run (no LLM), so results are stable and reproducible."
        actions={
          <button
            onClick={() => load(true)}
            disabled={loading}
            className="btn-ghost"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
            Re-run evaluation
          </button>
        }
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          {error}
        </div>
      )}

      {report && s && (
        <>
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
                : "border-amber-200 bg-amber-50 text-amber-800"
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
