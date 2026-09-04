"use client";

import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileSearch,
  Fingerprint,
  Gauge,
  HardHat,
  Languages,
  LifeBuoy,
  ListChecks,
  MessageSquareWarning,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import type { AnalysisResult, RuleCondition } from "@/lib/api";
import { PriorityBadge, SifBadge } from "@/components/Badges";

const CONDITION_META: Record<
  RuleCondition["status"],
  { label: string; chip: string; icon: React.ElementType; iconCls: string; row: string }
> = {
  breached: {
    label: "Breached",
    chip: "rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-700",
    icon: ShieldX,
    iconCls: "bg-red-100 text-red-600",
    row: "border-red-100 bg-red-50/40",
  },
  in_place: {
    label: "In place",
    chip: "rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-green-700",
    icon: CheckCircle2,
    iconCls: "bg-green-100 text-green-600",
    row: "border-green-100 bg-green-50/40",
  },
  not_verifiable: {
    label: "Not verifiable",
    chip: "rounded-full border border-amber-300/70 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-700",
    icon: FileSearch,
    iconCls: "bg-white text-amber-600 ring-1 ring-amber-300/70",
    row: "border-amber-300/50",
  },
};

const LANG_LABELS: Record<string, string> = {
  en: "English",
  hi: "हिन्दी · Hindi",
  "hi-latn": "Hindi (roman)",
  bn: "বাংলা · Bengali",
  "bn-latn": "Bengali (roman)",
  as: "অসমীয়া · Assamese",
  "as-latn": "Assamese (roman)",
};

function Field({
  icon: Icon,
  label,
  value,
  children,
}: {
  icon: React.ElementType;
  label: string;
  value?: string | null;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-brand-100 bg-white p-3.5">
      <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
        <Icon size={13} className="text-brand-500" />
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold text-ink">
        {children ?? value ?? <span className="font-normal text-ink-muted">Not specified</span>}
      </div>
    </div>
  );
}

const FACTOR_META: Record<
  string,
  { label: string; hint: string; max: number }
> = {
  indicators: {
    label: "Matched SIF indicators",
    hint: "Number of precursor indicators found in the text (capped at 3)",
    max: 3,
  },
  severity: {
    label: "Consequence severity",
    hint: "+2 when the potential consequence mentions fatality / serious injury, else +1",
    max: 2,
  },
  exposure: {
    label: "People exposure",
    hint: "+1 when the report shows people were exposed (workers/actors present)",
    max: 1,
  },
  barrier_failure: {
    label: "Barrier failure",
    hint: "+1 when a control was missing, defeated or bypassed",
    max: 1,
  },
};

function ScoreBreakdown({
  factors,
  priority,
}: {
  factors: Record<string, number>;
  priority: string | null;
}) {
  const entries = Object.entries(factors).filter(([, v]) => v > 0);
  const total = Object.values(factors).reduce((s, v) => s + v, 0);
  const tiers =
    priority === "HIGH"
      ? "5+ → HIGH · 3–4 → MEDIUM · below → LOW"
      : priority === "MEDIUM"
        ? "3–4 → MEDIUM (HIGH needs 5+)"
        : "below 3 → LOW";
  return (
    <div className="mt-3 rounded-xl border border-brand-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-brand-600">
          <Fingerprint size={12} /> Priority score — how it was calculated
        </p>
        <span className="text-[11px] font-semibold text-ink-muted">
          total <b className="text-brand-700">{total}</b> → threshold: {tiers}
        </span>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {entries.length === 0 && (
          <p className="text-xs text-ink-muted sm:col-span-2">
            No factors contributed — the report scored below the LOW threshold.
          </p>
        )}
        {entries.map(([key, value]) => {
          const meta = FACTOR_META[key];
          if (!meta) return null;
          const bar = Math.min(100, Math.round((value / meta.max) * 100));
          return (
            <div
              key={key}
              className="rounded-lg border border-brand-100 bg-brand-50/40 px-3 py-2"
              title={meta.hint}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-ink">{meta.label}</span>
                <span className="rounded-md bg-brand-100 px-1.5 py-0.5 font-mono text-[11px] font-extrabold text-brand-700">
                  +{value}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-brand-100">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                  style={{ width: `${bar}%` }}
                />
              </div>
              <p className="mt-1 text-[10.5px] leading-snug text-ink-muted">
                {meta.hint}
              </p>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-[10.5px] leading-relaxed text-ink-muted">
        Additive prototype score — not an official OIL risk methodology.
        Requires HSE validation before acting on the priority.
      </p>
    </div>
  );
}

export default function AnalysisResultCard({
  result,
  heading = "AI Analysis",
}: {
  result: AnalysisResult;
  heading?: string;
}) {
  const pct = result.confidence != null ? Math.round(result.confidence * 100) : null;

  // Legacy “Data note …” import crosscheck flags are not surfaced in the UI
  // anymore (the Field Coverage panel states the same in a cleaner way).
  const note =
    result.uncertainty_note &&
    !result.uncertainty_note.startsWith("Data note")
      ? result.uncertainty_note
      : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-brand-100 bg-brand-50/60 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-100 bg-white px-5 py-3">
        <h3 className="flex items-center gap-2 text-sm font-bold text-ink">
          <MessageSquareWarning size={16} className="text-brand-600" />
          {heading}
        </h3>
        <div className="flex items-center gap-2">
          {result.llm_refined && (
            <span className="badge badge-pink">LLM-refined</span>
          )}
          <span className="font-mono text-[11px] text-ink-muted">{result.model}</span>
        </div>
      </div>

      <div className="p-5">
        {/* Verdict row */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-brand-200 bg-white p-4">
          <span
            className={`grid h-12 w-12 place-items-center rounded-xl ${
              result.sif_potential
                ? "bg-brand-600 text-white"
                : "bg-green-100 text-green-700"
            }`}
          >
            {result.sif_potential ? (
              <AlertTriangle size={22} />
            ) : (
              <ShieldCheck size={22} />
            )}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-extrabold tracking-tight">
                {result.sif_potential ? "SIF Potential Detected" : "No SIF Precursor Detected"}
              </span>
              <SifBadge sif={result.sif_potential} />
            </div>
            <p className="text-xs text-ink-muted">
              {result.sif_potential
                ? "This report contains conditions with potential for serious injury or fatality."
                : "No serious-injury/fatality indicators were found in this report."}
            </p>
          </div>
        </div>

        {/* Confidence + priority */}
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-brand-100 bg-white p-3.5">
            <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              <Gauge size={13} className="text-brand-500" /> Confidence
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-2xl font-extrabold">{pct ?? "—"}%</span>
              {result.confidence != null && (
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-brand-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              )}
            </div>
          </div>
          <div className="rounded-xl border border-brand-100 bg-white p-3.5">
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              AI-Assisted Priority
            </div>
            <div className="mt-1.5">
              <PriorityBadge priority={result.priority} />
              <span className="ml-2 text-[10px] text-ink-muted">
                prototype · requires HSE validation
              </span>
            </div>
          </div>
          <div className="rounded-xl border border-brand-100 bg-white p-3.5">
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              Detection
            </div>
            <div className="mt-1.5">
              <SifBadge sif={result.sif_potential} />
              {result.unsafe_type && (
                <span className="ml-2 text-xs font-semibold text-ink-soft">
                  {result.unsafe_type}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Priority score breakdown — transparent, additive, explainable */}
        {result.priority_factors &&
          Object.keys(result.priority_factors).length > 0 && (
            <ScoreBreakdown
              factors={result.priority_factors}
              priority={result.priority}
            />
          )}

        {/* Languages detected */}
        {result.languages?.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 rounded-xl border border-brand-100 bg-white px-3.5 py-2.5">
            <span className="mr-1 inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              <Languages size={12} className="text-brand-500" /> Languages
            </span>
            {result.languages.map((code) => (
              <span
                key={code}
                className="badge border border-brand-100 bg-brand-50 text-brand-700"
                title={`Script detected in the original report (${code})`}
              >
                {LANG_LABELS[code] ?? code}
              </span>
            ))}
          </div>
        )}

        {/* Plain-language summary */}
        {result.summary && (
          <div className="mt-3 rounded-xl border border-brand-100 bg-white p-4">
            <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-brand-600">
              <MessageSquareWarning size={12} /> In plain language
            </p>
            <div className="mt-2 space-y-2">
              {result.summary.split(/\n\s*\n/).map((part, idx) => {
                const sep = part.indexOf("—");
                const head =
                  sep > 0 ? part.slice(0, sep).trim() : `Part ${idx + 1}`;
                const body = sep > 0 ? part.slice(sep + 1).trim() : part;
                return (
                  <p key={idx} className="flex items-start gap-2 text-sm leading-relaxed text-ink-soft">
                    <b className="mt-0.5 flex-shrink-0 rounded-md bg-brand-50 px-1.5 py-0.5 text-[10.5px] font-bold uppercase tracking-wide text-brand-700">
                      {head}
                    </b>
                    <span>{body}</span>
                  </p>
                );
              })}
            </div>
          </div>
        )}

        {/* Structured fields */}
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Field icon={ShieldX} label="Life-Saving Rule" value={result.life_saving_rule} />
          <Field icon={Fingerprint} label="Hazard" value={result.hazard} />
          <Field icon={ShieldCheck} label="Activity" value={result.activity} />
          <Field icon={FileSearch} label="Location" value={result.location} />
          <Field icon={HardHat} label="Equipment">
            {result.equipment.length ? (
              <div className="flex flex-wrap gap-1.5">
                {result.equipment.map((e) => (
                  <span key={e} className="badge border border-brand-100 bg-brand-50 text-brand-700">
                    {e}
                  </span>
                ))}
              </div>
            ) : (
              <span className="font-normal text-ink-muted">Not specified</span>
            )}
          </Field>
          <Field icon={LifeBuoy} label="Barrier Failure">
            {result.barrier_failure.length ? (
              <div className="flex flex-wrap gap-1.5">
                {result.barrier_failure.map((b) => (
                  <span key={b} className="badge badge-pink">{b}</span>
                ))}
              </div>
            ) : (
              <span className="font-normal text-ink-muted">Not specified</span>
            )}
          </Field>
          <Field icon={AlertTriangle} label="Potential Consequence" value={result.potential_consequence} />
        </div>

        {/* Rule-condition map — how the report maps to the Life-Saving Rule */}
        {result.rule_conditions && result.rule_conditions.length > 0 && (
          <div className="mt-4 rounded-xl border border-brand-200 bg-white p-4">
            <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-brand-600">
              <ShieldX size={12} /> Life-Saving-Rule conditions
              {result.life_saving_rule && (
                <span className="normal-case text-ink-muted">
                  — how this report maps to “{result.life_saving_rule}”
                </span>
              )}
            </p>
            <ul className="mt-3 space-y-1.5">
              {result.rule_conditions.map((c, i) => {
                const meta = CONDITION_META[c.status];
                const StatusIcon = meta.icon;
                return (
                  <li
                    key={i}
                    className={`flex items-start gap-2.5 rounded-xl border px-3 py-2 ${meta.row}`}
                  >
                    <span
                      className={`mt-0.5 grid h-6 w-6 flex-shrink-0 place-items-center rounded-lg ${meta.iconCls}`}
                    >
                      <StatusIcon size={13} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                        <p className="text-sm font-semibold leading-snug text-ink">
                          {c.condition}
                        </p>
                        <span className={meta.chip}>{meta.label}</span>
                      </div>
                      {c.evidence.length > 0 ? (
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wide text-ink-muted">
                            Report says:
                          </span>
                          {c.evidence.map((ev) => (
                            <span
                              key={ev}
                              className="rounded-md bg-white px-1.5 py-0.5 text-xs italic leading-relaxed text-ink-soft"
                            >
                              “{ev}”
                            </span>
                          ))}
                        </div>
                      ) : (
                        c.status === "not_verifiable" && (
                          <p className="mt-0.5 text-[11px] text-ink-muted">
                            The report does not mention this requirement.
                          </p>
                        )
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="mt-2.5 text-[10.5px] leading-relaxed text-ink-muted">
              Machine-mapped from the report text against the rule’s conditions
              — each “Breached” item quotes the exact wording it was inferred
              from. Validate with HSE before acting.
            </p>
          </div>
        )}

        {/* Evidence */}
        {result.evidence.length > 0 && (
          <div className="mt-4 rounded-xl border border-brand-200 border-l-4 border-l-brand-500 bg-white p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-brand-600">
              Evidence — from the original report
            </p>
            <ul className="mt-2 space-y-1.5">
              {result.evidence.map((e) => (
                <li key={e} className="flex items-start gap-2 text-sm text-ink-soft">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-brand-400" />
                  “{e}”
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Explanation */}
        {result.explanation && (
          <div className="mt-3 rounded-xl bg-white p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              Why was this flagged?
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
              {result.explanation}
            </p>
          </div>
        )}

        {/* Suggested actions checklist */}
        {result.suggested_actions?.length > 0 && (
          <div className="mt-3 rounded-xl border border-green-100 bg-green-50/60 p-4">
            <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-green-700">
              <ListChecks size={12} /> Suggested corrective actions
            </p>
            <ul className="mt-2 space-y-1.5">
              {result.suggested_actions.map((action) => (
                <li key={action} className="flex items-start gap-2 text-sm text-ink-soft">
                  <CheckCircle2 size={14} className="mt-0.5 flex-shrink-0 text-green-600" />
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Follow-up */}
        {result.recommended_follow_up && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            <ArrowRight size={16} className="mt-0.5 flex-shrink-0" />
            <span>
              <b>Recommended follow-up:</b> {result.recommended_follow_up}
            </span>
          </div>
        )}

        {note && (
          <div className="mt-3 rounded-lg border border-amber-300 bg-white p-3 text-xs leading-relaxed text-amber-900">
            <b>⚠️ Review flag:</b> {note}
          </div>
        )}
      </div>
    </div>
  );
}