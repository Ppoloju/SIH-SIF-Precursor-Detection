"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, Menu, Moon, ShieldAlert, Sun, X } from "lucide-react";
import { api } from "@/lib/api";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/analyze", label: "Analyze" },
  { href: "/ingest", label: "Import Data" },
  { href: "/reports", label: "Reports" },
  { href: "/rules", label: "Rules" },
  { href: "/sites", label: "Sites" },
  { href: "/activities", label: "Activities" },
  { href: "/barriers", label: "Barriers" },
  { href: "/patterns", label: "Patterns" },
  { href: "/evaluation", label: "Evaluation" },
];

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [live, setLive] = useState<{ ok: boolean; total?: number }>({ ok: false });

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Keep the toggle in sync with the boot script / external changes.
  useEffect(() => {
    const sync = () => setDark(document.documentElement.classList.contains("dark"));
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

  // Show a live "backend connected · N reports" pill when the API is reachable.
  useEffect(() => {
    let cancelled = false;
    api
      .getOverview()
      .then((o) => {
        if (!cancelled) setLive({ ok: true, total: o.total_reports });
      })
      .catch(() => {
        if (!cancelled) setLive({ ok: false });
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-40 border-b border-brand-100 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2.5">
          <span className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
            <ShieldAlert size={18} />
          </span>
          <span className="hidden truncate text-sm font-bold tracking-tight text-ink min-[380px]:block">
            SIF Precursor Detection
          </span>
        </Link>

        <nav className="hidden items-center gap-0.5 lg:flex">
          {links.map((l) => {
            const active = isActive(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`relative rounded-lg px-3 py-2 text-[13px] font-medium transition ${
                  active
                    ? "bg-brand-100 text-brand-700"
                    : "text-ink-soft hover:bg-brand-50 hover:text-brand-700"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
            className="grid h-9 w-9 place-items-center rounded-lg border border-brand-200 text-ink-soft transition hover:bg-brand-50 hover:text-brand-700"
          >
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {live.ok && (
            <span
              className="hidden items-center gap-1.5 rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-[11px] font-semibold text-green-700 sm:inline-flex"
              title="Backend connected — analytics computed from the database"
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
              Live · {live.total} reports
            </span>
          )}

          <button
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close navigation" : "Open navigation"}
            className="grid h-9 w-9 place-items-center rounded-lg border border-brand-200 text-ink-soft transition hover:bg-brand-50 hover:text-brand-700 lg:hidden"
          >
            {open ? <X size={17} /> : <Menu size={17} />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="border-t border-brand-100 bg-white/95 px-4 pb-5 pt-2 backdrop-blur lg:hidden">
          <nav className="grid grid-cols-2 gap-1.5">
            {links.map((l) => {
              const active = isActive(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                    active
                      ? "bg-brand-100 text-brand-700"
                      : "text-ink-soft hover:bg-brand-50"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
          <Link
            href="/ingest"
            className="mt-3 flex items-center justify-center gap-2 rounded-xl border border-dashed border-brand-300 bg-brand-50/60 px-3 py-2.5 text-sm font-semibold text-brand-700"
          >
            <Database size={15} />
            Import your HSSE dataset
          </Link>
          {live.ok && (
            <p className="mt-3 text-center text-[11px] font-semibold text-green-700">
              ● Backend connected — {live.total} reports in the database
            </p>
          )}
        </div>
      )}
    </header>
  );
}
