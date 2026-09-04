"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowRight, ShieldX } from "lucide-react";
import { api } from "@/lib/api";
import type { RuleStat } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";
import LifeSavingRulesLink from "@/components/RulesGuide";

export default function RulesPage() {
  const [rules, setRules] = useState<RuleStat[]>([]);
  const [sifTotal, setSifTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getLifeSavingRules()
      .then((d) => {
        setRules(d.rules);
        setSifTotal(d.sif_total);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const max = Math.max(...rules.map((r) => r.count), 1);
  const exportRows = rules.map((r) => ({
    "Life-Saving Rule": r.rule,
    Reports: r.count,
    "% of SIF-potential reports": r.percentage,
  }));

  return (
    <div>
      <PageHeader
        kicker="Analytics"
        title="Life-Saving Rule Analytics"
        icon={ShieldX}
        lede="Which Life-Saving Rules attract the most SIF precursors. The taxonomy is configurable and requires HSE/OIL validation."
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <LifeSavingRulesLink
              asLink
              label="What are these rules?"
            />
            <ExportButton rows={exportRows} filename="sif-life-saving-rules" />
          </div>
        }
      />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="card">
        <div className="space-y-3">
          {rules.map((r) => (
            <Link
              key={r.rule}
              href={`/reports?rule=${encodeURIComponent(r.rule)}`}
              title={`Open all ${r.count} reports mapped to “${r.rule}” in the Reports registry`}
              className="group -mx-2 flex items-center gap-4 rounded-xl border border-transparent px-2 py-1.5 transition hover:border-brand-200 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <span className="flex w-48 shrink-0 items-center gap-1 truncate text-sm font-semibold text-ink transition group-hover:text-brand-700">
                <ShieldX size={13} className="shrink-0 text-brand-500" />
                <span className="truncate">{r.rule}</span>
              </span>
              <span className="h-6 flex-1 overflow-hidden rounded-lg bg-brand-50">
                <span
                  className="flex h-full items-center rounded-lg bg-gradient-to-r from-brand-400 to-brand-600 pl-2 text-[11px] font-bold text-white transition group-hover:from-brand-500 group-hover:to-brand-700"
                  style={{ width: `${Math.max((r.count / max) * 100, 4)}%` }}
                >
                  {r.count}
                </span>
              </span>
              <span className="flex w-24 shrink-0 items-center justify-end gap-1 font-mono text-xs text-ink-muted transition group-hover:text-brand-700">
                {r.percentage}%
                <ArrowRight
                  size={13}
                  className="shrink-0 opacity-0 transition group-hover:translate-x-0.5 group-hover:opacity-100"
                />
              </span>
            </Link>
          ))}
          {rules.length === 0 && (
            <p className="py-8 text-center text-sm text-ink-muted">No rule data yet.</p>
          )}
        </div>
        <p className="mt-4 text-[11px] text-ink-muted">
          Percentages are of {sifTotal} SIF-potential reports. Click any
          Life-Saving Rule — its name, bar or count — to open all of its
          reports in the registry, already filtered.
        </p>
      </div>
    </div>
  );
}