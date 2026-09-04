"use client";

import type { LucideIcon } from "lucide-react";

/**
 * Consistent section banner used at the top of every page:
 * kicker chip, icon mark, title, lede and optional right-hand actions.
 */
export default function PageHeader({
  kicker,
  title,
  lede,
  icon: Icon,
  actions,
  tint = "brand",
}: {
  kicker: string;
  title: string;
  lede?: React.ReactNode;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  tint?: "brand" | "amber";
}) {
  const isAmber = tint === "amber";
  return (
    <div className="relative mb-8 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-white px-6 py-7 shadow-soft sm:px-8">
      {/* decorative blobs */}
      <div className="pointer-events-none absolute -right-16 -top-24 h-56 w-56 rounded-full bg-brand-200/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-28 right-24 h-44 w-44 rounded-full bg-brand-100/50 blur-3xl" />

      <div className="relative flex flex-wrap items-start justify-between gap-x-8 gap-y-4">
        <div className="flex min-w-0 items-start gap-4">
          {Icon && (
            <span
              className={`grid h-12 w-12 flex-shrink-0 place-items-center rounded-2xl text-white shadow-md ${
                isAmber
                  ? "bg-gradient-to-br from-amber-500 to-orange-600"
                  : "bg-gradient-to-br from-brand-500 to-brand-700"
              }`}
            >
              <Icon size={22} />
            </span>
          )}
          <div className="min-w-0">
            <span className="kicker">{kicker}</span>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
              {title}
            </h1>
            {lede && (
              <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-ink-muted">
                {lede}
              </p>
            )}
          </div>
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2.5">{actions}</div>
        )}
      </div>
    </div>
  );
}
