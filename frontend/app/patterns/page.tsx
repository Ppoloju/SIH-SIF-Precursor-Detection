"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Repeat } from "lucide-react";
import { api } from "@/lib/api";
import type { Pattern } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getPatterns()
      .then((d) => {
        setPatterns(d.patterns);
        setNote(d.note ?? "");
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
        lede="What safety problems are repeatedly occurring and where? Patterns are mined from structured fields and reported only when they actually recur — nothing is fabricated."
        actions={
          <ExportButton rows={exportRows} filename="sif-recurring-patterns" />
        }
      />

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" /> {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {patterns.map((p) => (
          <div key={p.title} className="card border-l-4 border-l-brand-500">
            <div className="flex items-start justify-between gap-3">
              <h2 className="flex items-center gap-2 text-base font-bold">
                <Repeat size={16} className="text-brand-500" />
                {p.title}
              </h2>
              <span className="badge badge-pink">
                {p.count} {p.count === 1 ? "report" : "reports"}
              </span>
            </div>
            <p className="mt-2 text-sm text-ink-soft">{p.detail}</p>
            <p className="mt-3 font-mono text-[11px] uppercase tracking-wide text-brand-600">
              {p.type}
            </p>
          </div>
        ))}
        {patterns.length === 0 && (
          <div className="card md:col-span-2">
            <p className="py-8 text-center text-sm text-ink-muted">
              No recurring patterns detected yet — patterns appear once enough
              similar reports exist.
            </p>
          </div>
        )}
      </div>
      {note && <p className="mt-4 text-[11px] text-ink-muted">{note}</p>}
    </div>
  );
}