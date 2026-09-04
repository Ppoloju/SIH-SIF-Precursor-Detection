"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, LifeBuoy } from "lucide-react";
import { api } from "@/lib/api";
import type { BarrierStat } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

export default function BarriersPage() {
  const [barriers, setBarriers] = useState<BarrierStat[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getBarriers()
      .then((d) => {
        setBarriers(d.barriers);
        setNote(d.note ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const max = Math.max(...barriers.map((b) => b.count), 1);
  const exportRows = barriers.map((b) => ({
    "Barrier Failure": b.barrier,
    Reports: b.count,
    Sites: b.sites,
    Activities: b.activities,
    "Life-Saving Rules": b.rules,
    "Example reports": b.examples.map((e) => e.report_id),
  }));

  return (
    <div>
      <PageHeader
        kicker="Analytics"
        title="Barrier Failure Analysis"
        icon={LifeBuoy}
        lede="Which safety barriers are repeatedly failing? Each row answers that with counts, associated activities and example reports."
        actions={
          <ExportButton rows={exportRows} filename="sif-barrier-failures" />
        }
      />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="space-y-4">
        {barriers.map((b) => (
          <div key={b.barrier} className="card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 text-base font-bold">
                <LifeBuoy size={16} className="text-brand-500" />
                {b.barrier}
                <span className="badge badge-red">{b.count}</span>
              </h2>
              <div className="h-2 w-40 overflow-hidden rounded-full bg-brand-50">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                  style={{ width: `${(b.count / max) * 100}%` }}
                />
              </div>
            </div>
            <div className="mt-3 grid gap-3 text-xs sm:grid-cols-3">
              <div>
                <p className="font-bold uppercase tracking-wider text-ink-muted">Sites</p>
                <p className="mt-0.5 text-ink-soft">{b.sites.join(", ") || "—"}</p>
              </div>
              <div>
                <p className="font-bold uppercase tracking-wider text-ink-muted">Activities</p>
                <p className="mt-0.5 text-ink-soft">{b.activities.join(", ") || "—"}</p>
              </div>
              <div>
                <p className="font-bold uppercase tracking-wider text-ink-muted">Life-Saving Rules</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {b.rules.map((r) => (
                    <span key={r} className="badge badge-pink">{r}</span>
                  ))}
                  {b.rules.length === 0 && <span className="text-ink-muted">—</span>}
                </div>
              </div>
            </div>
            {b.examples.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-brand-50 pt-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                  Example reports:
                </span>
                {b.examples.map((ex) => (
                  <Link
                    key={ex.id}
                    href={`/reports/${ex.id}`}
                    className="rounded-lg border border-brand-200 px-2.5 py-1 font-mono text-xs font-semibold text-brand-700 hover:bg-brand-50"
                  >
                    {ex.report_id}
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {note && <p className="mt-4 text-[11px] text-ink-muted">{note}</p>}
    </div>
  );
}