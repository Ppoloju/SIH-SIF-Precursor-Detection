"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { BookOpenCheck, X } from "lucide-react";

/** Canonical IOGP-style Life-Saving Rules the AI maps reports to.
 *  Kept in sync with the backend taxonomy (backend/app/services/safety_lexicon.py). */
export const LIFE_SAVING_RULES = [
  {
    name: "Work Authorization",
    icon: "📝",
    desc: "Always work with a valid permit when required.",
  },
  {
    name: "Energy Isolation",
    icon: "⚡",
    desc: "Verify isolation and ensure zero energy before work begins.",
  },
  {
    name: "Bypassing Safety Controls",
    icon: "🔓",
    desc: "Obtain authorization before overriding or disabling any safety controls.",
  },
  {
    name: "Confined Space Entry",
    icon: "🕳️",
    desc: "Always obtain authorization and test the atmosphere before entering a confined space.",
  },
  {
    name: "Working at Height",
    icon: "🧗",
    desc: "Protect yourself against falls when working at height.",
  },
  {
    name: "Safe Mechanical Lifting",
    icon: "🏗️",
    desc: "Plan lifting operations carefully and control the area to prevent accidents.",
  },
  {
    name: "Toxic Gas Safety",
    icon: "☠️",
    desc: "Monitor air quality and follow procedures when working with toxic gases such as H2S.",
  },
  {
    name: "Driving Safety",
    icon: "🚗",
    desc: "Adhere to safe driving rules to prevent collisions and protect pedestrians.",
  },
  {
    name: "Line of Fire",
    icon: "🎯",
    desc: "Keep yourself and others out of the line of fire during operations.",
  },
  {
    name: "Hot Work Safety",
    icon: "🔥",
    desc: "Control flammable materials and ignition sources when performing hot work.",
  },
];

export default function LifeSavingRulesLink({
  compact = false,
  asLink = false,
  className = "",
  label = "Life-Saving Rules",
}: {
  compact?: boolean;
  /** Render as a small text hyperlink instead of an outlined chip. */
  asLink?: boolean;
  className?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);

  // Close on Escape and lock body scroll while the popup is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={label}
        aria-haspopup="dialog"
        aria-label={compact ? label : undefined}
        className={
          asLink
            ? `inline-flex items-center gap-1 text-xs font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 transition hover:text-brand-900 hover:decoration-brand-500 ${className}`
            : compact
              ? `inline-flex h-9 w-9 items-center justify-center rounded-lg border border-brand-200 text-ink-soft transition hover:bg-brand-50 hover:text-brand-700 ${className}`
              : `inline-flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3.5 py-2 text-xs font-bold text-brand-700 transition hover:border-brand-400 hover:bg-brand-50 ${className}`
        }
      >
        <BookOpenCheck size={compact ? 16 : 15} />
        {!compact && label}
      </button>

      {/* Portaled so the dialog never nests inside a <p>/<div> wherever the
          trigger link is placed (invalid HTML caused React hydration errors). */}
      {open &&
        createPortal(
        <div
          className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-ink/60 p-4 backdrop-blur-sm"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Life-Saving Rules"
        >
          <div
            className="w-full max-w-2xl animate-rise overflow-hidden rounded-3xl bg-white shadow-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative border-b border-brand-100 bg-gradient-to-br from-brand-50 via-white to-white px-6 py-5">
              <div className="flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
                  <BookOpenCheck size={20} />
                </span>
                <div>
                  <h2 className="text-lg font-extrabold tracking-tight">
                    10 Life-Saving Rules
                  </h2>
                  <p className="text-xs text-ink-muted">
                    The rules the AI maps every safety report to — IOGP-style
                    standards used by oil &amp; gas operators.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-lg border border-brand-200 bg-white text-ink-soft transition hover:bg-brand-50 hover:text-brand-700"
              >
                <X size={16} />
              </button>
            </div>

            <ul className="max-h-[55vh] divide-y divide-brand-50 overflow-y-auto px-6 py-2">
              {LIFE_SAVING_RULES.map((r, i) => (
                <li key={r.name} className="flex items-start gap-3.5 py-3">
                  <span className="font-mono text-[11px] font-bold text-brand-500">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="mt-0.5 text-base">{r.icon}</span>
                  <div>
                    <p className="text-sm font-bold text-ink">{r.name}</p>
                    <p className="text-[13px] leading-relaxed text-ink-muted">
                      {r.desc}
                    </p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="border-t border-brand-100 bg-brand-50/50 px-6 py-3.5 text-[11px] leading-relaxed text-ink-muted">
              The taxonomy is configurable and each mapping is stored with the
              report — reviewed and validated by HSE before it becomes an
              intervention.
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
