"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Database,
  FileText,
  FileUp,
  Flame,
  GitCompare,
  LayoutDashboard,
  LifeBuoy,
  Minus,
  Repeat,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
  UploadCloud,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyticsOverview, RuleStat, SiteStat } from "@/lib/api";
import { api } from "@/lib/api";
import { PriorityBadge, ReviewBadge, SifBadge } from "@/components/Badges";
import PageHeader from "@/components/PageHeader";
import ExportButton from "@/components/ExportButton";
import LifeSavingRulesLink from "@/components/RulesGuide";
import { useTheme } from "@/components/ThemeProvider";
import { chartPalette } from "@/lib/chartPalette";

const tipStyle = {
  borderRadius: 12,
  border: "1px solid var(--pop-line)",
  boxShadow: "var(--pop-shadow)",
  fontSize: 12,
  background: "var(--pop-bg)",
  color: "var(--pop-fg)",
};

function istUpdated(iso: string | null | undefined): string | null {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return null;
  }
}

/** Week-over-week change chip computed from real trend data (last two periods). */
function DeltaChip({
  cur,
  prev,
  tone = "slate",
  noun = "vs prev. week",
}: {
  cur?: number;
  prev?: number;
  tone?: "slate" | "pink";
  noun?: string;
}) {
  if (cur == null || prev == null || prev === 0) return null;
  const pct = Math.round(((cur - prev) / prev) * 100);
  if (pct === 0) {
    return (
      <span className="inline-flex items-center gap-0.5 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">
        <Minus size={11} /> 0% {noun}
      </span>
    );
  }
  const up = pct > 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] font-bold ${
        tone === "pink"
          ? up
            ? "bg-brand-100 text-brand-700"
            : "bg-green-100 text-green-700"
          : up
            ? "bg-slate-100 text-slate-700"
            : "bg-slate-100 text-slate-600"
      }`}
    >
      {up ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
      {Math.abs(pct)}% {noun}
    </span>
  );
}

export default function DashboardPage() {
  const mode = useTheme();
  const C = chartPalette(mode);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [rules, setRules] = useState<RuleStat[]>([]);
  const [sites, setSites] = useState<SiteStat[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [chartKind, setChartKind] = useState<
    "area" | "line" | "bar" | "composed"
  >("area");
  // Counts vs density metric for the same underlying trend data.
  const [chartMetric, setChartMetric] = useState<"counts" | "density">(
    "counts"
  );
  const [trendWindow, setTrendWindow] = useState<4 | 8>(8);
  const [activeRule, setActiveRule] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [ov, rl, st] = await Promise.all([
          api.getOverview(),
          api.getLifeSavingRules(),
          api.getSites(),
        ]);
        if (cancelled) return;
        setOverview(ov);
        setRules(rl.rules);
        setSites(st.sites);
        setError(null);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Backend unreachable");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    // Keep the dashboard fresh after data is imported elsewhere.
    // Today: refresh on focus + a light 20s poll while the tab is visible
    // (cheap GETs; the recommended next step is SSE push — see README).
    const refresh = () => {
      if (document.visibilityState === "visible") load();
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    const timer = window.setInterval(refresh, 20_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, []);

  const trend = useMemo(() => overview?.trend ?? [], [overview]);

  // Density view reuses the same weekly trend: SIF-potential ÷ reports × 100.
  const densityTrend = useMemo(
    () =>
      trend.map((t) => ({
        ...t,
        density:
          t.count > 0 ? Math.round((1000 * (t.sif_count ?? 0)) / t.count) / 10 : 0,
      })),
    [trend]
  );
  const visibleTrend = useMemo(
    () => trend.slice(-trendWindow),
    [trend, trendWindow]
  );
  const visibleDensityTrend = useMemo(
    () => densityTrend.slice(-trendWindow),
    [densityTrend, trendWindow]
  );
  const densityMode = chartMetric === "density";

  // Real week-over-week deltas from the last two periods of the trend.
  const deltas = useMemo(() => {
    if (visibleTrend.length < 2) return null;
    const last = visibleTrend[visibleTrend.length - 1];
    const prev = visibleTrend[visibleTrend.length - 2];
    return {
      lastPeriod: last.period,
      total: { cur: last.count, prev: prev.count },
      sif: { cur: last.sif_count, prev: prev.sif_count },
    };
  }, [visibleTrend]);

  const topSite = useMemo(
    () =>
      sites.length
        ? sites.reduce((a, b) => (b.count > a.count ? b : a))
        : null,
    [sites]
  );

  const topRuleStat = useMemo(
    () =>
      overview?.top_life_saving_rule
        ? rules.find((r) => r.rule === overview.top_life_saving_rule) ?? null
        : null,
    [rules, overview]
  );

  if (loading) {
    return (
      <div className="grid place-items-center py-32">
        <div className="flex flex-col items-center gap-3">
          <span className="h-9 w-9 animate-spin rounded-full border-[3px] border-brand-100 border-t-brand-600" />
          <p className="text-xs font-semibold text-ink-muted">
            Loading dashboard…
          </p>
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="card mx-auto max-w-xl">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 text-red-500" size={20} />
          <div>
            <h1 className="text-lg font-bold">Backend not reachable</h1>
            <p className="mt-1 text-sm text-ink-muted">{error}</p>
            <p className="mt-2 text-xs text-ink-muted">
              Start the FastAPI backend with{" "}
              <code className="rounded bg-brand-50 px-1.5 py-0.5 font-mono">
                uvicorn app.main:app --port 8000
              </code>{" "}
              in <code className="rounded bg-brand-50 px-1.5 py-0.5 font-mono">backend/</code>,
              then reload.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const density = overview.sif_density; // SIF / total, as a number
  const highPct =
    overview.total_reports > 0
      ? Math.round((100 * overview.high_priority_reports) / overview.total_reports)
      : 0;

  // Downloadable one-page HSE summary (single block, opens in Excel).
  const summaryRows = [
    { Metric: "Report", Value: "SIF Precursor Dashboard" },
    { Metric: "Generated (UTC)", Value: new Date().toISOString() },
    { Metric: "Reports analyzed", Value: overview.total_reports },
    { Metric: "SIF-potential reports", Value: overview.sif_potential_reports },
    { Metric: "SIF precursor density (%)", Value: density },
    { Metric: "High-priority reports", Value: overview.high_priority_reports },
    { Metric: "High-priority share (%)", Value: highPct },
    { Metric: "Top Life-Saving Rule", Value: overview.top_life_saving_rule ?? "" },
    { Metric: "Most common barrier failure", Value: overview.top_barrier_failure ?? "" },
    {
      Metric: "Most-reported site",
      Value: topSite ? `${topSite.site} (${topSite.count} reports)` : "",
    },
    {
      Metric: "Latest report date",
      Value: overview.latest_report_at ?? "",
    },
  ];
  // Note: the full report-by-report export (all filters + search) lives on the
  // Reports page; here we export the one-page HSE summary per the spec.
  const dashboardExportRows = summaryRows;

  return (
    <div className="animate-rise">
      <PageHeader
        kicker="HSE Overview"
        title="SIF Precursor Dashboard"
        icon={LayoutDashboard}
        lede={
          <>
            AI-assisted early-warning overview of serious-injury &amp; fatality
            precursors. {overview.note}
            {istUpdated(overview.latest_report_at) && (
              <span className="mt-1.5 flex items-center gap-1.5 text-[11px] font-medium text-ink-muted">
                <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                Data updated as of {istUpdated(overview.latest_report_at)} IST
              </span>
            )}
          </>
        }
        actions={
          <>
            <Link href="/ingest" className="btn-ghost">
              <FileUp size={15} /> Import Dataset
            </Link>
            <ExportButton
              rows={dashboardExportRows}
              filename="sif-dashboard"
              label="Export CSV"
            />
            <Link href="/analyze" className="btn-primary">
              <Sparkles size={16} /> Analyze a Report
            </Link>
          </>
        }
      />

      {/* ---- KPI row ---- */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {/* Total */}
        <div className="card flex flex-col">
          <div className="flex items-center justify-between">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-50 text-brand-600">
              <FileText size={17} />
            </span>
            <DeltaChip cur={deltas?.total.cur} prev={deltas?.total.prev} />
          </div>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
            Reports Analyzed
          </p>
          <p className="mt-0.5 text-3xl font-extrabold tracking-tight text-ink">
            {overview.total_reports}
          </p>
          <p className="mt-auto pt-1 text-xs text-ink-muted">
            UA · UC · Near-miss · Incident
          </p>
        </div>

        {/* SIF with density donut */}
        <div className="card flex flex-col">
          <div className="flex items-center justify-between">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-100 text-brand-600">
              <ShieldAlert size={17} />
            </span>
            <DeltaChip
              cur={deltas?.sif.cur}
              prev={deltas?.sif.prev}
              tone="pink"
              noun="vs prev. week"
            />
          </div>
          <div className="mt-4 flex items-center gap-4">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                SIF-Potential
              </p>
              <p className="text-3xl font-extrabold tracking-tight text-brand-600">
                {overview.sif_potential_reports}
              </p>
            </div>
            {/* density donut */}
            <div
              className="relative ml-auto h-16 w-16 rounded-full"
              style={{
                background: `conic-gradient(var(--sif) ${density * 3.6}deg, var(--sif-soft) 0deg)`,
              }}
              title={`SIF precursor density: ${density}%`}
            >
              <div className="absolute inset-[5px] grid place-items-center rounded-full bg-white">
                <span className="text-[13px] font-extrabold text-brand-700">
                  {Math.round(density)}%
                </span>
              </div>
            </div>
          </div>
          <p className="mt-auto pt-1 text-xs text-ink-muted">
            SIF precursor density = SIF-potential ÷ reports
          </p>
        </div>

        {/* High priority */}
        <div className="card flex flex-col">
          <div className="flex items-center justify-between">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-red-100 text-red-600">
              <Flame size={17} />
            </span>
            <span className="badge badge-red">{highPct}% of reports</span>
          </div>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
            High Priority
          </p>
          <p className="mt-0.5 text-3xl font-extrabold tracking-tight text-red-600">
            {overview.high_priority_reports}
          </p>
          <p className="mt-auto pt-1 text-xs text-ink-muted">
            AI-assisted ranking — requires HSE review
          </p>
        </div>

        {/* Top LSR */}
        <div className="card flex flex-col">
          <div className="flex items-center justify-between">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-50 text-brand-600">
              <LifeBuoy size={17} />
            </span>
            <TrendingUp size={15} className="text-brand-400" />
          </div>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
            Top Life-Saving Rule
          </p>
          <p className="mt-0.5 text-xl font-extrabold leading-snug tracking-tight text-ink">
            {overview.top_life_saving_rule ?? "—"}
          </p>
          <div className="mt-auto flex flex-wrap items-center gap-x-1.5 pt-1 text-xs text-ink-muted">
            <span>
              {topRuleStat
                ? `${topRuleStat.count} reports map here · ${topRuleStat.percentage}% of SIF-potential`
                : "Mapped from detected precursors"}
            </span>
            <span aria-hidden="true">·</span>
            <LifeSavingRulesLink asLink label="view rules" />
          </div>
        </div>
      </div>

      {/* ---- Focus strip ---- */}
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div className="card flex items-center gap-3 !p-4">
          <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600">
            <Target size={18} />
          </span>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
              Most-reported site
            </p>
            <p className="truncate text-sm font-bold text-ink">
              {topSite ? topSite.site : "—"}
            </p>
            <p className="text-[11px] text-ink-muted">
              {topSite ? `${topSite.count} reports · ${topSite.high} high-priority` : "no site data yet"}
            </p>
          </div>
        </div>
        <div className="card flex items-center gap-3 !p-4">
          <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl bg-red-50 text-red-600">
            <ShieldAlert size={18} />
          </span>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
              Most common barrier failure
            </p>
            <p className="truncate text-sm font-bold text-ink">
              {overview.top_barrier_failure ?? "—"}
            </p>
            <p className="text-[11px] text-ink-muted">
              Focus verification &amp; corrective action here
            </p>
          </div>
        </div>
        <div className="card flex items-center gap-3 !p-4">
          <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl bg-violet-100 text-violet-700">
            <Repeat size={18} />
          </span>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
              Recurring precursor patterns
            </p>
            {overview.patterns.length ? (
              <>
                <p className="truncate text-sm font-bold text-ink">
                  {overview.patterns[0].title}
                </p>
                <p className="text-[11px] text-ink-muted">
                  {overview.patterns[0].count} reports —{" "}
                  <Link href="/patterns" className="font-semibold text-brand-700 hover:underline">
                    view all
                  </Link>
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-bold text-ink">None surfaced yet</p>
                <p className="text-[11px] text-ink-muted">
                  <Link href="/patterns" className="font-semibold text-brand-700 hover:underline">
                    Pattern analytics →
                  </Link>
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {overview.total_reports > 0 ? (
        <>
          {/* ---- Charts ---- */}
          <div className="mt-6 grid gap-4 lg:grid-cols-5">
        <div className="card lg:col-span-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="card-title">
              <TrendingUp size={16} className="text-brand-600" /> SIF Precursor
              Trend
            </h2>
            <div className="flex flex-wrap items-center gap-1.5">
              <div
                className="flex items-center gap-0.5 rounded-lg border border-brand-200 bg-brand-50/60 p-0.5"
                role="group"
                aria-label="Trend time range"
              >
                {([4, 8] as const).map((windowSize) => (
                  <button
                    key={windowSize}
                    onClick={() => setTrendWindow(windowSize)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-bold transition ${
                      trendWindow === windowSize
                        ? "bg-white text-brand-700 shadow-sm"
                        : "text-ink-muted hover:text-brand-600"
                    }`}
                    aria-pressed={trendWindow === windowSize}
                    title={`Show the last ${windowSize} weeks`}
                  >
                    {windowSize}W
                  </button>
                ))}
              </div>
              {/* Metric toggle — counts or SIF density % (same underlying data) */}
              <div
                className="flex items-center gap-0.5 rounded-lg border border-brand-200 bg-brand-50/60 p-0.5"
                role="group"
                aria-label="Trend metric"
              >
                {(
                  [
                    ["counts", "Counts"],
                    ["density", "Density %"],
                  ] as const
                ).map(([metric, label]) => (
                  <button
                    key={metric}
                    onClick={() => setChartMetric(metric)}
                    title={
                      metric === "density"
                        ? "SIF-potential ÷ all reports per week, as a percentage"
                        : "Raw weekly report counts"
                    }
                    className={`rounded-md px-2.5 py-1 text-[11px] font-bold transition ${
                      chartMetric === metric
                        ? "bg-white text-brand-700 shadow-sm"
                        : "text-ink-muted hover:text-brand-600"
                    }`}
                    aria-pressed={chartMetric === metric}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {/* Chart-type switch — area / line / bar / composed (bar + line) */}
              <div
                className="flex items-center gap-0.5 rounded-lg border border-brand-200 bg-brand-50/60 p-0.5"
                role="group"
                aria-label="Trend chart type"
              >
                {(
                  [
                    ["area", "Area"],
                    ["line", "Line"],
                    ["bar", "Bar"],
                    ["composed", "Bar + line"],
                  ] as const
                ).map(([kind, label]) => (
                  <button
                    key={kind}
                    onClick={() => setChartKind(kind)}
                    title={
                      kind === "composed"
                        ? "Bar for all reports with the SIF-potential overlaid as a line"
                        : `Show the trend as a ${label.toLowerCase()} chart`
                    }
                    className={`rounded-md px-2.5 py-1 text-[11px] font-bold transition ${
                      chartKind === kind
                        ? "bg-white text-brand-700 shadow-sm"
                        : "text-ink-muted hover:text-brand-600"
                    }`}
                    aria-pressed={chartKind === kind}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <span className="hidden text-xs font-medium text-ink-muted sm:inline">
              {deltas
                ? `latest week: ${deltas.lastPeriod}`
                : "last 8 weeks"}
            </span>
          </div>
          <div className="mt-4 h-60 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              {chartKind === "area" ? (
                <AreaChart data={densityMode ? visibleDensityTrend : visibleTrend}>
                  <defs>
                    <linearGradient id="sifFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={C.sif} stopOpacity={0.32} />
                      <stop offset="100%" stopColor={C.sif} stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="allFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={C.all} stopOpacity={0.22} />
                      <stop offset="100%" stopColor={C.all} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} allowDecimals={false} width={28} />
                  <Tooltip contentStyle={tipStyle} cursor={{ stroke: C.focus, strokeDasharray: "4 4" }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" iconSize={9} />
                  {densityMode ? (
                    <Area
                      type="monotone"
                      dataKey="density"
                      name="SIF density (%)"
                      stroke={C.sif}
                      strokeWidth={2.5}
                      fill="url(#sifFill)"
                      dot={{ r: 3, fill: C.sif, strokeWidth: 0 }}
                      activeDot={{ r: 5 }}
                    />
                  ) : (
                    <>
                      <Area
                        type="monotone"
                        dataKey="count"
                        name="All reports"
                        stroke={C.all}
                        strokeWidth={2}
                        fill="url(#allFill)"
                        dot={false}
                      />
                      <Area
                        type="monotone"
                        dataKey="sif_count"
                        name="SIF-potential"
                        stroke={C.sif}
                        strokeWidth={2.5}
                        fill="url(#sifFill)"
                        dot={{ r: 3, fill: C.sif, strokeWidth: 0 }}
                        activeDot={{ r: 5 }}
                      />
                    </>
                  )}
                </AreaChart>
              ) : chartKind === "line" ? (
                <LineChart data={densityMode ? visibleDensityTrend : visibleTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} allowDecimals={false} width={28} />
                  <Tooltip contentStyle={tipStyle} cursor={{ stroke: C.focus, strokeDasharray: "4 4" }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" iconSize={9} />
                  {densityMode ? (
                    <Line
                      type="monotone"
                      dataKey="density"
                      name="SIF density (%)"
                      stroke={C.sif}
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: C.sif, strokeWidth: 0 }}
                      activeDot={{ r: 5 }}
                    />
                  ) : (
                    <>
                      <Line
                        type="monotone"
                        dataKey="count"
                        name="All reports"
                        stroke={C.all}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="sif_count"
                        name="SIF-potential"
                        stroke={C.sif}
                        strokeWidth={2.5}
                        dot={{ r: 3, fill: C.sif, strokeWidth: 0 }}
                        activeDot={{ r: 5 }}
                      />
                    </>
                  )}
                </LineChart>
              ) : chartKind === "composed" ? (
                <ComposedChart data={densityMode ? visibleDensityTrend : visibleTrend} barGap={2}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} allowDecimals={false} width={28} />
                  <Tooltip contentStyle={tipStyle} cursor={{ fill: C.barCursor }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" iconSize={9} />
                  {densityMode ? (
                    <Bar dataKey="density" name="SIF density (%)" fill={C.sif} radius={[4, 4, 0, 0]} maxBarSize={18} />
                  ) : (
                    <>
                      <Bar dataKey="count" name="All reports" fill={C.all} radius={[4, 4, 0, 0]} maxBarSize={18} />
                      <Line
                        type="monotone"
                        dataKey="sif_count"
                        name="SIF-potential"
                        stroke={C.sif}
                        strokeWidth={2.5}
                        dot={{ r: 3, fill: C.sif, strokeWidth: 0 }}
                        activeDot={{ r: 5 }}
                      />
                    </>
                  )}
                </ComposedChart>
              ) : (
                <BarChart data={densityMode ? visibleDensityTrend : visibleTrend} barGap={2}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} stroke={C.axis} tickLine={false} axisLine={false} allowDecimals={false} width={28} />
                  <Tooltip contentStyle={tipStyle} cursor={{ fill: C.barCursor }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" iconSize={9} />
                  {densityMode ? (
                    <Bar dataKey="density" name="SIF density (%)" fill={C.sif} radius={[4, 4, 0, 0]} maxBarSize={18} />
                  ) : (
                    <>
                      <Bar dataKey="count" name="All reports" fill={C.all} radius={[4, 4, 0, 0]} maxBarSize={18} />
                      <Bar dataKey="sif_count" name="SIF-potential" fill={C.sif} radius={[4, 4, 0, 0]} maxBarSize={18} />
                    </>
                  )}
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
          {deltas && (
            <div className="mt-2 flex flex-wrap gap-2 border-t border-brand-50 pt-3 text-[11px] text-ink-muted">
              <span className="font-semibold uppercase tracking-wider">
                vs previous week ({deltas.lastPeriod}):
              </span>
              <DeltaChip cur={deltas.total.cur} prev={deltas.total.prev} noun="all reports" />
              <DeltaChip cur={deltas.sif.cur} prev={deltas.sif.prev} tone="pink" noun="SIF-potential" />
            </div>
          )}
        </div>

        <div className="card lg:col-span-2">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="card-title">
                <BarChart3 size={16} className="text-brand-600" /> Life-Saving Rule
                Distribution
              </h2>
              <p className="mt-1 text-[11px] text-ink-muted">Select a segment to inspect its share of SIF-potential reports.</p>
            </div>
            <LifeSavingRulesLink asLink compact={false} label="Rules" />
          </div>
          <div className="mt-3 grid items-center gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(150px,0.9fr)]">
            <div className="h-56 min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={rules}
                    dataKey="count"
                    nameKey="rule"
                    cx="50%"
                    cy="50%"
                    innerRadius="52%"
                    outerRadius="78%"
                    paddingAngle={2}
                    onClick={(entry) => setActiveRule(String(entry.payload?.rule ?? ""))}
                    onMouseEnter={(entry) => setActiveRule(String(entry.payload?.rule ?? ""))}
                    isAnimationActive
                  >
                    {rules.map((entry, index) => (
                      <Cell
                        key={entry.rule}
                        fill={C.pie[index % C.pie.length]}
                        opacity={activeRule && activeRule !== entry.rule ? 0.38 : 1}
                        stroke="var(--card-bg)"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={tipStyle}
                    formatter={(value, _name, item) => [
                      `${value} reports (${item.payload.percentage}%)`,
                      "SIF-potential",
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="min-w-0">
              <div className="mb-2 rounded-lg bg-brand-50/70 px-3 py-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">Selected rule</p>
                <p className="mt-0.5 truncate text-sm font-extrabold text-ink">
                  {activeRule ?? "Hover a segment"}
                </p>
                <p className="text-[11px] text-ink-muted">
                  {activeRule ? `${rules.find((rule) => rule.rule === activeRule)?.count ?? 0} reports` : `${rules.length} mapped rules`}
                </p>
              </div>
              <div className="max-h-40 space-y-1 overflow-y-auto pr-1">
                {rules.map((entry, index) => (
                  <button
                    key={entry.rule}
                    onClick={() => setActiveRule(activeRule === entry.rule ? null : entry.rule)}
                    className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[11px] transition ${
                      activeRule === entry.rule ? "bg-brand-50 text-brand-700" : "text-ink-muted hover:bg-brand-50/60"
                    }`}
                    aria-pressed={activeRule === entry.rule}
                  >
                    <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ backgroundColor: C.pie[index % C.pie.length] }} />
                    <span className="min-w-0 flex-1 truncate">{entry.rule}</span>
                    <span className="font-bold text-ink">{entry.count}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="mt-2 border-t border-brand-50 pt-3 text-[11px] text-ink-muted">
            Percentages are calculated from SIF-potential reports. Rule taxonomy requires HSE/OIL validation.
          </p>
        </div>
      </div>

      {/* ---- Table + patterns ---- */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="card-title">
              <Flame size={16} className="text-brand-600" /> Recent High-Priority
              Reports
            </h2>
            <Link
              href="/reports?priority=HIGH"
              className="text-xs font-semibold text-brand-700 hover:underline"
            >
              Open review queue →
            </Link>
          </div>
          <div className="table-wrap mt-3">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead>
                <tr className="table-head">
                  <th className="px-3 py-2.5">Report</th>
                  <th className="px-3 py-2.5">Date</th>
                  <th className="px-3 py-2.5">Site</th>
                  <th className="px-3 py-2.5">SIF</th>
                  <th className="px-3 py-2.5">Priority</th>
                  <th className="px-3 py-2.5">Rule</th>
                  <th className="px-3 py-2.5">Similar</th>
                  <th className="px-3 py-2.5">Review</th>
                </tr>
              </thead>
              <tbody>
                {overview.recent_high_priority.map((r) => (
                  <tr key={r.id} className="table-row">
                    <td className="px-3 py-2.5">
                      <Link
                        href={`/reports/${r.id}`}
                        className="font-mono text-xs font-semibold text-brand-700 hover:underline"
                      >
                        {r.report_id}
                      </Link>
                    </td>
                    <td className="px-3 py-2.5 text-xs text-ink-soft">{r.date ?? "—"}</td>
                    <td className="px-3 py-2.5 text-xs text-ink-soft">{r.site ?? "—"}</td>
                    <td className="px-3 py-2.5">
                      <SifBadge sif={r.analysis?.sif_potential ?? false} />
                    </td>
                    <td className="px-3 py-2.5">
                      <PriorityBadge priority={r.analysis?.priority ?? null} />
                    </td>
                    <td className="px-3 py-2.5 text-xs text-ink-soft">
                      {r.analysis?.life_saving_rule ?? "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      {r.similar_reports.length > 0 ? (
                        <Link
                          href={`/reports/${r.id}`}
                          title={`${r.similar_reports.length} similar past report(s) — see them on the report page`}
                          className="badge border border-brand-200 bg-brand-50 text-brand-700 transition hover:bg-brand-100"
                        >
                          <GitCompare size={11} /> {r.similar_reports.length} similar
                        </Link>
                      ) : (
                        <span className="text-xs text-ink-muted">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <ReviewBadge status={r.review_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">
            <Activity size={16} className="text-brand-600" /> Recurring Patterns
          </h2>
          <div className="mt-3 space-y-3">
            {overview.patterns.length === 0 ? (
              <Link
                href="/patterns"
                className="block rounded-xl border border-dashed border-brand-200 bg-brand-50/50 p-4 text-center text-xs font-semibold text-brand-700 hover:bg-brand-50"
              >
                View recurring pattern analytics →
              </Link>
            ) : (
              overview.patterns.map((p) => (
                <div key={p.title} className="rounded-xl border border-brand-100 bg-brand-50/60 p-3.5">
                  <p className="text-sm font-bold text-ink">{p.title}</p>
                  <p className="mt-0.5 text-xs text-ink-muted">{p.detail}</p>
                  <p className="mt-1.5 font-mono text-xs font-bold text-brand-600">
                    {p.count} report{p.count > 1 ? "s" : ""}
                  </p>
                </div>
              ))
            )}
            <p className="pt-1 text-[11px] text-ink-muted">
              Patterns are mined from available data only — never fabricated.
            </p>
          </div>
        </div>
      </div>
        </>
      ) : (
        <DatabaseEmptyState />
      )}
    </div>
  );
}

function DatabaseEmptyState() {
  return (
    <div className="mt-8 rounded-3xl border-2 border-dashed border-brand-200 bg-gradient-to-b from-brand-50/60 to-white px-6 py-14 text-center">
      <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
        <Database size={24} />
      </span>
      <h2 className="mt-5 text-xl font-extrabold tracking-tight">
        Your database is empty — ready for real data
      </h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-ink-muted">
        No safety reports yet. Import any CSV / Excel / JSON export from your
        HSSE platform — any column layout works. Every row is stored in
        PostgreSQL, analyzed by the SIF engine, and the dashboard updates live.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Link href="/ingest" className="btn-primary">
          <UploadCloud size={16} /> Import your dataset
        </Link>
        <Link href="/analyze" className="btn-ghost">
          <Sparkles size={16} /> Or analyze a single report
        </Link>
      </div>
      <div className="mx-auto mt-8 flex max-w-xl flex-wrap items-center justify-center gap-2 text-[11px] font-semibold text-ink-muted">
        <span className="rounded-full border border-brand-200 bg-white px-3 py-1">1 · Upload file</span>
        <span>→</span>
        <span className="rounded-full border border-brand-200 bg-white px-3 py-1">2 · Auto column mapping</span>
        <span>→</span>
        <span className="rounded-full border border-brand-200 bg-white px-3 py-1">3 · PostgreSQL + SIF analysis</span>
        <span>→</span>
        <span className="rounded-full border border-brand-200 bg-white px-3 py-1">4 · Live dashboard</span>
      </div>
      <p className="mt-6 text-[11px] text-ink-muted">
        Demo seeding is disabled for this clean database (SEED_DEMO_DATA=0). If
        you want the synthetic demo reports back, restart the backend with
        SEED_DEMO_DATA=1.
      </p>
    </div>
  );
}
