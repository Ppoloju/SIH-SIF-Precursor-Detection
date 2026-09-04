"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  ClipboardCheck,
  FileText,
  FlaskConical,
  HardHat,
  LayoutDashboard,
  MapPin,
  Menu,
  Moon,
  ShieldAlert,
  ShieldCheck,
  Sun,
  Upload,
  Wand2,
  X,
} from "lucide-react";
import { api } from "@/lib/api";

/**
 * Navigation lives in a fixed LEFT SIDEBAR (desktop) so the user always knows
 * where they are; a compact top bar + slide-in drawer covers mobile.
 *
 * Layout contract: pages render inside `lg:pl-64` (see app/layout.tsx) so the
 * rail never overlaps content. Section labels are static text; every clickable
 * item carries an icon + filled active pill so links and headings never look
 * the same.
 */
const workLinks = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/review", label: "HSE Review", icon: ClipboardCheck, badge: true },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/analyze", label: "Analyze", icon: Wand2 },
  { href: "/ingest", label: "Import Data", icon: Upload },
];

const PAGE_TITLES: [string, string][] = [
  ["/", "Dashboard"],
  ["/review", "HSE Review"],
  ["/reports", "Reports"],
  ["/analyze", "Analyze"],
  ["/ingest", "Import Data"],
  ["/rules", "Life-Saving Rules"],
  ["/patterns", "Recurring Patterns"],
  ["/sites", "Site Risk"],
  ["/activities", "Activities"],
  ["/barriers", "Barrier Failures"],
  ["/evaluation", "Model Evaluation"],
];

const insightLinks = [
  { href: "/rules", label: "Life-Saving Rules", icon: ShieldCheck },
  { href: "/patterns", label: "Recurring Patterns", icon: Activity },
  { href: "/sites", label: "Site Risk", icon: MapPin },
  { href: "/activities", label: "Activities", icon: HardHat },
  { href: "/barriers", label: "Barrier Failures", icon: BarChart3 },
  { href: "/evaluation", label: "Model Evaluation", icon: FlaskConical },
];

type Counts = { ok: boolean; total?: number; pending?: number };

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [counts, setCounts] = useState<Counts>({ ok: false });

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    const sync = () =>
      setDark(document.documentElement.classList.contains("dark"));
    sync();
    window.addEventListener("sif-theme", sync);
    return () => window.removeEventListener("sif-theme", sync);
  }, []);

  const toggleTheme = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    document.documentElement.style.colorScheme = next ? "dark" : "light";
    try {
      localStorage.setItem("sif-theme", next ? "dark" : "light");
    } catch {}
    setDark(next);
    window.dispatchEvent(new Event("sif-theme"));
  };

  // Live badge state: backend up + report totals + pending HSE reviews.
  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const [ov, cnt] = await Promise.all([
          api.getOverview(),
          api.getReportCounts(),
        ]);
        if (!cancelled)
          setCounts({ ok: true, total: ov.total_reports, pending: cnt.pending });
      } catch {
        if (!cancelled) setCounts({ ok: false });
      }
    }
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };
    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const currentTitle =
    PAGE_TITLES.find(([p]) =>
      p === "/" ? pathname === "/" : pathname.startsWith(p)
    )?.[1] ?? "Dashboard";

  const sections = (
    <>
      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        <NavGroup label="Work">
          {workLinks.map((l) => (
            <NavItem
              key={l.href}
              href={l.href}
              label={l.label}
              icon={l.icon}
              active={isActive(l.href)}
              badge={l.badge ? counts.pending ?? 0 : 0}
            />
          ))}
        </NavGroup>
        <NavGroup label="Insights · Analytics & learning">
          {insightLinks.map((l) => (
            <NavItem
              key={l.href}
              href={l.href}
              label={l.label}
              icon={l.icon}
              active={isActive(l.href)}
            />
          ))}
        </NavGroup>
      </div>

      <div className="border-t border-brand-100 p-3">
        <div className="rounded-xl border border-brand-100 bg-brand-50/40 px-3 py-2.5">
          {counts.ok ? (
            <>
              <p className="flex items-center gap-1.5 text-[11px] font-bold text-green-700">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                </span>
                Backend live
              </p>
              <p className="mt-0.5 truncate text-[10px] text-ink-muted">
                {counts.total} reports · {counts.pending} awaiting review
              </p>
            </>
          ) : (
            <p className="text-[11px] font-semibold text-ink-muted">
              Backend offline — start the API
            </p>
          )}
        </div>
        <p className="mt-2.5 text-center text-[10px] leading-relaxed text-ink-muted">
          Prototype · AI-assisted · Requires HSE/OIL validation
        </p>
      </div>
    </>
  );

  return (
    <>
      {/* ---- Desktop: top header — theme switch lives here ---- */}
      <header className="sticky top-0 z-30 hidden border-b border-brand-100 bg-white/90 backdrop-blur lg:block">
        <div className="flex h-14 items-center justify-between gap-3 pl-64 pr-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-extrabold tracking-tight text-ink">
              {currentTitle}
            </p>
            <p className="truncate text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">
              SIF Precursor Detection · HSE Intelligence
            </p>
          </div>
          <div className="flex items-center gap-2">
            {counts.ok && (
              <span
                className="hidden items-center gap-1.5 rounded-full border border-brand-100 bg-brand-50/60 px-2.5 py-1 text-[10.5px] font-bold text-green-700 xl:inline-flex"
                title={`${counts.total} reports · ${counts.pending} awaiting HSE review`}
              >
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                </span>
                {counts.pending} awaiting HSE review
              </span>
            )}
            <button
              onClick={toggleTheme}
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              title={dark ? "Switch to light mode" : "Switch to dark mode"}
              className="grid h-9 w-9 place-items-center rounded-lg border border-brand-200 bg-white text-ink-soft transition hover:bg-brand-50 hover:text-brand-700"
            >
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </div>
      </header>

      {/* ---- Desktop: fixed left rail ---- */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-brand-100 bg-white lg:flex">
        <BrandLink />
        {sections}
      </aside>

      {/* ---- Mobile: compact top bar ---- */}
      <header className="sticky top-0 z-40 border-b border-brand-100 bg-white/90 backdrop-blur lg:hidden">
        <div className="flex h-14 items-center justify-between gap-3 px-4">
          <BrandLink compact />
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              className="grid h-9 w-9 place-items-center rounded-lg border border-brand-200 text-ink-soft"
            >
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button
              onClick={() => setOpen((v) => !v)}
              aria-label={open ? "Close navigation" : "Open navigation"}
              aria-expanded={open}
              className="grid h-9 w-9 place-items-center rounded-lg border border-brand-200 text-ink-soft"
            >
              {open ? <X size={17} /> : <Menu size={17} />}
            </button>
          </div>
        </div>
        {counts.ok && (
          <p className="border-t border-brand-50 px-4 py-1.5 text-[10px] font-semibold text-green-700">
            ● Backend live — {counts.total} reports · {counts.pending} awaiting
            HSE review
          </p>
        )}
      </header>

      {/* ---- Mobile drawer ---- */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-[19rem] max-w-[85vw] flex-col bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-brand-100 px-4 py-3">
              <BrandLink compact />
              <button
                onClick={() => setOpen(false)}
                aria-label="Close navigation"
                className="grid h-8 w-8 place-items-center rounded-lg border border-brand-200 text-ink-soft"
              >
                <X size={15} />
              </button>
            </div>
            {sections}
          </div>
        </div>
      )}
    </>
  );
}

function BrandLink({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      href="/"
      className="flex items-center gap-3 border-b border-brand-100 px-4 py-4"
      title="Back to dashboard"
    >
      <span className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-brand-700 text-white shadow-sm">
        <ShieldAlert size={18} />
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-sm font-extrabold tracking-tight text-ink">
          SIF Precursor Detection
        </span>
        {!compact && (
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">
            HSE early-warning platform
          </span>
        )}
      </span>
    </Link>
  );
}

function NavGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-ink-muted">
        {label}
      </p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function NavItem({
  href,
  label,
  icon: Icon,
  active,
  badge = 0,
}: {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  active: boolean;
  badge?: number;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      title={label}
      className={`relative flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-semibold transition ${
        active
          ? "bg-brand-100 text-brand-700"
          : "text-ink-soft hover:bg-brand-50 hover:text-brand-700"
      }`}
    >
      <Icon
        size={16}
        strokeWidth={2.2}
        className={active ? "text-brand-600" : "text-ink-muted"}
      />
      <span className="flex-1 truncate">{label}</span>
      {badge > 0 && (
        <span
          className="grid h-5 min-w-[20px] place-items-center rounded-full bg-amber-400 px-1 text-[10px] font-extrabold text-amber-950"
          title={`${badge} report(s) still need an HSE decision`}
        >
          {badge}
        </span>
      )}
      {active && <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-brand-600" />}
    </Link>
  );
}
