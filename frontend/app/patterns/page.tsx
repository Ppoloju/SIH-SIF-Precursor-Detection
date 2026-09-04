"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  FlaskConical,
  Info,
  MapPin,
  Repeat,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Pattern } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

/** Open the real reports that form this pattern, pre-filtered in the registry. */
function registryHref(p: Pattern): string {
  const qs = new URLSearchParams(
    Object.entries(p.filters ?? {}).filter(([, v]) => v)
  ).toString();
  return `/reports${qs ? `?${qs}` : ""}`;
}

const TYPE_TONES: Record<string, string> = {
  "rule + activity": "bg-brand-100 text-brand-700",
  "rule + barrier": "bg-orange-100 text-orange-700",
  "hazard + activity": "bg-violet-100 text-violet-700",
};

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [note, setNote] = useState("");
  const [criteria, setCriteria] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showCriteria, setShowCriteria] = useState(false);

  useEffect(() => {
    api
      .getPatterns()
      .then((d) => {
        setPatterns(d.patterns);
        setNote(d.note ?? "");
        setCriteria(d.criteria ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const exportRows = patterns.map((p) => ({
    Pattern: p.title,
    Type: p.type,
    Reports: p.count,
    Detail: p.detail,
  }));

  return (
    <div>
      <PageHeader
        kicker="Analytics"
        title="Recurring Pattern Detection"
        icon={Repeat}
        lede="What safety problems keep recurring and where? Every pattern below is backed by the real reports that formed it — click a pattern to open those reports, or an individual ID to see its similar history."
        actions={
          <>
            <button
              onClick={() => setShowCriteria(true)}
              className="btn-ghost"
            >
              <Info size={15} /> How patterns are found
            </button>
            <ExportButton rows={exportRows} filename="sif-recurring-patterns" />
          </>
        }
      />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
        </div>
      )}

      {patterns.length === 0 && !error ? (
        <div className="card">
          <p className="py-10 text-center text-sm text-ink-muted">
            No recurring patterns detected yet — patterns appear once enough
            similar SIF-potential reports exist.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {patterns.map((p) => (
            <article
              key={`${p.type}-${p.title}`}
              className="card flex flex-col transition hover:border-brand-300"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      TYPE_TONES[p.type] ?? "bg-brand-100 text-brand-700"
                    }`}
                  >
                    {p.type}
                  </span>
                  <span className="badge badge-red">
                    {p.count} {p.count === 1 ? "report" : "reports"}
                  </span>
                </div>
              </div>

              <h2 className="mt-3 text-base font-bold leading-snug text-ink">
                <Link
                  href={registryHref(p)}
                  title={`Open the ${p.count} real reports behind this pattern`}
                  className="hover:underline"
                >
                  {p.title}
                </Link>
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                {p.detail}
              </p>

              {/* Real member reports (up to 3) — click an ID to open that
                  report with its own similar-history view. */}
              {p.examples && p.examples.length > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                    Reports in this pattern:
                  </span>
                  {p.examples.map((ex) => (
                    <Link
                      key={ex.id}
                      href={`/reports/${ex.id}`}
                      title={`${ex.site ?? "Site not stated"} — opens the report and its similar history`}
                      className="inline-flex items-center gap-1 rounded-lg border border-brand-200 bg-white px-2 py-0.5 font-mono text-[11px] font-semibold text-brand-700 transition hover:border-brand-400 hover:bg-brand-50"
                    >
                      <MapPin size={9} className="text-ink-muted" />
                      {ex.report_id}
                    </Link>
                  ))}
                </div>
              )}

              <div className="mt-auto border-t border-brand-50 pt-3">
                <Link
                  href={registryHref(p)}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-700 hover:underline"
                >
                  Open all {p.count} matching reports in the registry
                  <ArrowRight size={13} />
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}

      {note && <p className="mt-4 text-[11px] text-ink-muted">{note}</p>}

      {/* “How patterns are found” popup */}
      {showCriteria && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm"
          onClick={() => setShowCriteria(false)}
          role="dialog"
          aria-modal="true"
          aria-label="How recurring patterns are found"
        >
          <div
            className="card max-h-[85vh] w-full max-w-lg overflow-y-auto !p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <h2 className="card-title">
                <FlaskConical size={17} className="text-brand-600" />
                How are patterns found?
              </h2>
              <button
                onClick={() => setShowCriteria(false)}
                aria-label="Close"
                className="grid h-8 w-8 place-items-center rounded-lg border border-brand-200 text-ink-muted hover:bg-brand-50 hover:text-ink"
              >
                <X size={15} />
              </button>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">
              {criteria ||
                "A pattern = the same combination of structured fields on 2 or more SIF-potential reports."}
            </p>
            <ul className="mt-4 space-y-2.5 text-sm text-ink-soft">
              <li className="flex items-start gap-2.5">
                <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-brand-500" />
                <span>
                  <b className="text-ink">Rule + activity</b> — e.g. “Energy
                  Isolation during maintenance”: the same Life-Saving Rule keeps
                  triggering during the same kind of work.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-orange-500" />
                <span>
                  <b className="text-ink">Rule + barrier failure</b> — the same
                  control keeps failing (e.g. isolation not verified) under one
                  rule.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-violet-500" />
                <span>
                  <b className="text-ink">Hazard + activity</b> — the same
                  hazard recurs during one activity.
                </span>
              </li>
            </ul>
            <p className="mt-4 rounded-xl bg-brand-50/70 p-3 text-xs leading-relaxed text-ink-muted">
              Patterns are mined only from the reports actually stored in the
              database, and only when the combination recurs at least twice —
              nothing is fabricated. Click a pattern to open its real member
              reports in the registry; open a member ID to see that report’s
              similar history and HSE review state.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
