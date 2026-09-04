"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowUpRight, LifeBuoy } from "lucide-react";
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

  const exportRows = barriers.map((b) => ({
    "Barrier Failure": b.barrier,
    Reports: b.count,
    Sites: b.sites,
    Activities: b.activities,
    "Life-Saving Rules": b.rules,
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
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-brand-50 pt-3 text-xs">
              <Link
                href={`/reports?barrier=${encodeURIComponent(b.barrier)}`}
                title={`Open the ${b.count} real reports that failed this barrier in the registry — each opens with its own similar history`}
                className="inline-flex items-center gap-1.5 font-bold text-brand-700 hover:underline"
              >
                Open the {b.count} matching reports <ArrowUpRight size={13} />
              </Link>
              {b.count > 3 && (
                <span className="text-ink-muted">
                  (more than 3 — the registry shows all of them)
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      {note && <p className="mt-4 text-[11px] text-ink-muted">{note}</p>}
    </div>
  );
}