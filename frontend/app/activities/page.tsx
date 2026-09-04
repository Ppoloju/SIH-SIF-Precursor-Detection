"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Wrench } from "lucide-react";
import { api } from "@/lib/api";
import type { ActivityStat } from "@/lib/api";
import { PriorityBadge } from "@/components/Badges";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

export default function ActivitiesPage() {
  const [activities, setActivities] = useState<ActivityStat[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getActivities()
      .then((d) => {
        setActivities(d.activities);
        setNote(d.note ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const exportRows = activities.map((a) => ({
    Activity: a.activity,
    Reports: a.count,
    "High priority": a.priority_distribution.HIGH ?? 0,
    "Medium priority": a.priority_distribution.MEDIUM ?? 0,
    "Low priority": a.priority_distribution.LOW ?? 0,
    "Major hazards": a.main_hazards,
    "Barrier failures": a.main_barriers,
    "Life-Saving Rules": a.main_rules,
  }));

  return (
    <div>
      <PageHeader
        kicker="Analytics"
        title="Activity Analytics"
        icon={Wrench}
        lede="Activities associated with SIF precursors — where do serious-injury potentials keep appearing?"
        actions={
          <ExportButton rows={exportRows} filename="sif-activity-risk" />
        }
      />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {activities.map((a) => (
          <div key={a.activity} className="card">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-bold">
                <Wrench size={15} className="text-brand-500" />
                {a.activity}
              </h2>
              <span className="text-2xl font-extrabold text-brand-600">{a.count}</span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <PriorityBadge priority="HIGH" />
              <span className="text-xs text-ink-soft">{a.priority_distribution.HIGH ?? 0}</span>
              <PriorityBadge priority="MEDIUM" />
              <span className="text-xs text-ink-soft">{a.priority_distribution.MEDIUM ?? 0}</span>
              <PriorityBadge priority="LOW" />
              <span className="text-xs text-ink-soft">{a.priority_distribution.LOW ?? 0}</span>
            </div>
            <dl className="mt-3 space-y-2 text-xs">
              <div>
                <dt className="font-bold uppercase tracking-wider text-ink-muted">Major hazards</dt>
                <dd className="mt-0.5 text-ink-soft">{a.main_hazards.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-bold uppercase tracking-wider text-ink-muted">Barrier failures</dt>
                <dd className="mt-1 flex flex-wrap gap-1.5">
                  {a.main_barriers.map((b) => (
                    <span key={b} className="badge badge-pink">{b}</span>
                  ))}
                  {a.main_barriers.length === 0 && <span className="text-ink-muted">—</span>}
                </dd>
              </div>
              <div>
                <dt className="font-bold uppercase tracking-wider text-ink-muted">Life-Saving Rules</dt>
                <dd className="mt-0.5 text-ink-soft">{a.main_rules.join(", ") || "—"}</dd>
              </div>
            </dl>
          </div>
        ))}
      </div>
      {note && <p className="mt-4 text-[11px] text-ink-muted">{note}</p>}
    </div>
  );
}