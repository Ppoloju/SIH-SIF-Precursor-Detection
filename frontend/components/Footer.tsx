import { Cpu, Database, ShieldAlert } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-10 border-t border-brand-100 bg-gradient-to-b from-white to-brand-50/70 px-4 pb-10 pt-8">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-4 text-center">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white">
            <ShieldAlert size={14} />
          </span>
          <p className="text-sm font-extrabold tracking-tight text-brand-700">
            SIH SIF Precursor Detection
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] font-semibold text-ink-muted">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1">
            <Database size={11} className="text-brand-500" />
            PostgreSQL pipeline
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1">
            <Cpu size={11} className="text-brand-500" />
            Hybrid NLP + optional LLM
          </span>
          <span className="rounded-full border border-amber-300 bg-white px-3 py-1 text-amber-700">
            Prototype · AI-assisted · Requires HSE/OIL validation
          </span>
        </div>

        <p className="max-w-2xl text-xs leading-relaxed text-ink-muted">
          AI/NLP engine to detect Serious Injury &amp; Fatality (SIF) precursors
          in Unsafe-Act / Unsafe-Condition and Near-Miss reports. Smart India
          Hackathon · Problem Statement 26165 · Oil India Limited. Demo reports
          are synthetic; imported datasets keep their provenance labels.
        </p>
      </div>
    </footer>
  );
}
