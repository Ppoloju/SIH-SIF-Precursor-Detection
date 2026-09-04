"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import type { SiteStat } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

export default function SitesPage() {
  const [sites, setSites] = useState<SiteStat[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSites()
      .then((d) => {
        setSites(d.sites);
        setNote(d.note ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const max = Math.max(...sites.map((s) => s.count), 1);
  const exportRows = sites.map((s) => ({
    Site: s.site,
    Reports: s.count,
    "High-priority reports": s.high,
    "Main hazards": s.main_hazards,
    "Main Life-Saving Rules": s.main_rules,
  }));

  return (
    <div>
      <PageHeader
        kicker="Analytics"
        title="Site Risk Analytics"
        icon={MapPin}
        lede="Locations with the highest SIF-precursor activity — ranked so HSSE can focus interventions where fatal potential is highest."
        actions={
          <ExportButton rows={exportRows} filename="sif-site-risk" />
        }
      />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sites.map((s) => (
          <div key={s.site} className="card">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-bold">
                <MapPin size={15} className="text-brand-500" />
                {s.site}
              </h2>
              <span className="text-2xl font-extrabold text-brand-600">{s.count}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-brand-50">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
                style={{ width: `${(s.count / max) * 100}%` }}
              />
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="font-bold uppercase tracking-wider text-ink-muted">High priority</p>
                <p className="mt-0.5 text-base font-extrabold text-red-600">{s.high}</p>
              </div>
              <div>
                <p className="font-bold uppercase tracking-wider text-ink-muted">Main hazards</p>
                <p className="mt-0.5 text-ink-soft">{s.main_hazards.join(", ") || "—"}</p>
              </div>
              <div className="col-span-2">
                <p className="font-bold uppercase tracking-wider text-ink-muted">Main rules</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {s.main_rules.map((r) => (
                    <span key={r} className="badge badge-pink">{r}</span>
                  ))}
                  {s.main_rules.length === 0 && <span className="text-ink-muted">—</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      {note && <p className="mt-4 text-[11px] text-ink-muted">{note}</p>}
    </div>
  );
}