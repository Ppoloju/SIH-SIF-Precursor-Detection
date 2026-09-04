// Frontend API client for the FastAPI backend.

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type Priority = "HIGH" | "MEDIUM" | "LOW" | null;
export type ReviewStatus =
  | "pending"
  | "confirmed"
  | "rejected"
  | "edited"
  | "reviewed";

export interface RuleCondition {
  condition: string;
  status: "breached" | "in_place" | "not_verifiable";
  evidence: string[];
}

/** One file-provided structured value that replaced the AI text-extraction.
 *  `changed: true` = the AI produced a different value -> UI shows “Y”. */
export interface AnalysisOverride {
  field: string;
  canonical: string;
  ai: string | null;
  used: string;
  changed: boolean;
}

export interface Report {
  id: number;
  report_id: string;
  report_text: string;
  report_type: string | null;
  date: string | null;
  site: string | null;
  activity: string | null;
  is_demo: boolean;
  source: string | null;
  source_id: string | null;
  processing_status: string;
  created_at: string;
}

export interface Analysis {
  id: number;
  report_id: number;
  sif_potential: boolean;
  confidence: number | null;
  priority: Priority;
  hazard: string | null;
  potential_consequence: string | null;
  barrier_failure: string[] | null;
  life_saving_rule: string | null;
  activity: string | null;
  location: string | null;
  equipment: string[] | null;
  unsafe_type: string | null;
  evidence: string[] | null;
  rule_conditions: RuleCondition[] | null;
  modified_fields: AnalysisOverride[] | null;
  explanation: string | null;
  recommended_follow_up: string | null;
  summary: string | null;
  suggested_actions: string[] | null;
  languages: string[] | null;
  uncertainty_note: string | null;
  priority_factors: Record<string, number> | null;
  model: string | null;
}

export interface AnalysisResult {
  sif_potential: boolean;
  confidence: number | null;
  priority: Priority;
  hazard: string | null;
  hazards: string[];
  potential_consequence: string | null;
  barrier_failure: string[];
  life_saving_rule: string | null;
  activity: string | null;
  location: string | null;
  equipment: string[];
  unsafe_type: string | null;
  evidence: string[];
  rule_conditions: RuleCondition[];
  explanation: string | null;
  recommended_follow_up: string | null;
  summary: string | null;
  suggested_actions: string[];
  languages: string[];
  model: string | null;
  llm_refined: boolean;
  uncertainty_note: string | null;
  priority_factors: Record<string, number>;
}

export interface Review {
  id: number;
  report_id: number;
  reviewer: string | null;
  decision: string | null;
  corrected_priority: Priority;
  corrected_rule: string | null;
  comments: string | null;
  reviewed_at: string | null;
}

export interface ReportDetail extends Report {
  analysis: Analysis | null;
  review: Review | null;
  review_status: ReviewStatus;
  similar_reports: SimilarReport[];
  /** Set when the closest stored match is a near-copy (possible duplicate). */
  duplicate_of?: SimilarReport | null;
}

export interface SimilarReport {
  id: number;
  report_id: string;
  similarity: number;
  common_hazard: string | null;
  common_activity: string | null;
  common_barrier: string[] | null;
  common_rule: string | null;
  // Review context of the matched report (set by the API) — used to surface
  // a *solved* similar case at another site as the reference for this one.
  site?: string | null;
  decision?: ReviewStatus | null;
  reviewer?: string | null;
  comments?: string | null;
  corrected_rule?: string | null;
  corrected_priority?: Priority;
  reviewed_at?: string | null;
}

// ---------------------------------------------------------------------------
// Evaluation + feedback (golden set + human-in-the-loop training)
// ---------------------------------------------------------------------------
export interface ConfusionMetrics {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
}

export interface RuleMetric extends ConfusionMetrics {
  rule: string;
  support: number;
}

export interface EvalCase {
  id: string;
  lang: string;
  language_label: string;
  text: string;
  expected_sif: boolean;
  detected_sif: boolean;
  sif_match: boolean;
  expected_rules: string[];
  detected_rules: string[];
  rule_match: boolean;
  confidence: number | null;
  priority: Priority;
  languages_detected: string[];
}

export interface CvFold extends ConfusionMetrics {
  fold: number;
  n: number;
  sif_positive: number;
  languages: string;
}

export interface CvAggregate {
  mean: number;
  std: number;
  min: number;
  max: number;
  ci95_low: number;
  ci95_high: number;
}

export interface CrossValidation {
  k: number;
  n_cases: number;
  folds: CvFold[];
  aggregate: Record<"precision" | "recall" | "f1" | "accuracy", CvAggregate>;
  runtime_ms: number;
  methodology: string;
}

export interface EvaluationReport {
  generated_at: string;
  dataset: { name: string; total: number; note?: string };
  sif_classification: ConfusionMetrics;
  rules: RuleMetric[];
  languages: { lang: string; label: string; cases: number; sif_correct: number; sif_accuracy: number }[];
  multilingual: { cases: number; sif_correct: number; sif_accuracy: number | null };
  cases: EvalCase[];
  runtime_ms: number;
  methodology: string;
  cross_validation?: CrossValidation | null;
}

export interface LearnedSignal {
  phrase: string;
  direction: string;
  reports?: number;
  why?: string;
}

export interface TrainingRun {
  id?: number;
  feedback_count?: number;
  metrics?: ConfusionMetrics | null;
  signals?: LearnedSignal[] | null;
  note?: string | null;
  created_at?: string | null;
}

export interface FeedbackSummary {
  feedback_count: number;
  labeled_for_training: number;
  by_decision: Record<string, number>;
  latest_run: TrainingRun | null;
  note?: string;
}

export interface TrainResponse {
  ok: boolean;
  run_id: number;
  feedback_count: number;
  metrics: ConfusionMetrics;
  signals: LearnedSignal[];
  human_model_agreement: number;
  note?: string;
}

export interface TrendPoint {
  period: string;
  count: number;
  sif_count: number;
}

export interface AnalyticsOverview {
  total_reports: number;
  sif_potential_reports: number;
  sif_density: number;
  high_priority_reports: number;
  top_life_saving_rule: string | null;
  top_barrier_failure: string | null;
  trend: TrendPoint[];
  recent_high_priority: ReportDetail[];
  patterns: { title: string; detail: string; count: number }[];
  latest_report_at?: string | null;
  note?: string;
}

export interface RuleStat {
  rule: string;
  count: number;
  percentage: number;
}

export interface SiteStat {
  site: string;
  count: number;
  high: number;
  main_hazards: string[];
  main_rules: string[];
}

export interface ActivityStat {
  activity: string;
  count: number;
  priority_distribution: Record<string, number>;
  main_hazards: string[];
  main_barriers: string[];
  main_rules: string[];
}

export interface BarrierStat {
  barrier: string;
  count: number;
  sites: string[];
  activities: string[];
  rules: string[];
  examples: { id: number; report_id: string }[];
}

export interface Pattern {
  type: string;
  title: string;
  detail: string;
  count: number;
  /** Registry filters that open the real reports forming this pattern. */
  filters?: {
    rule?: string;
    activity?: string;
    hazard?: string;
    barrier?: string;
  };
  /** Up to 3 real member reports (id + platform ID + site). */
  examples?: { id: number; report_id: string; site: string | null }[];
}

export interface PatternResponse {
  patterns: Pattern[];
  note?: string;
  criteria?: string;
}

/** Ingest column mapping: canonical field -> column name | null (explicit none). */
export type FieldMapping = Partial<
  Record<
    | "text"
    | "title"
    | "date"
    | "site"
    | "activity"
    | "report_type"
    | "report_id"
    | "hazard"
    | "consequence"
    | "barrier_failure"
    | "location"
    | "equipment"
    | "unsafe_type"
    | "rule",
    string | null
  >
>;

export interface IngestSample {
  text: string | null;
  report_type: string | null;
  date: string | null;
  site: string | null;
  activity: string | null;
}

export interface IngestPreview {
  columns: string[];
  mapping: Record<string, string | null>;
  canonicals: string[];
  total_rows: number;
  samples: IngestSample[];
  note?: string;
}

export interface IngestFailure {
  row: number;
  error: string;
}

export interface IngestJobStart {
  job_id: number;
  status: "running" | "done" | "error";
  rows_total: number;
  source?: string | null;
  filename?: string | null;
  mapping?: Record<string, string | null>;
}

export interface IngestJobState extends IngestJobStart {
  processed: number;
  imported: number;
  skipped_empty: number;
  failed_count: number;
  sif_potential: number;
  high_priority: number;
  first_report_id: string | null;
  failures: IngestFailure[];
  duplicate_count?: number;
  duplicates?: { row: number; duplicate_of: string }[];
  error: string | null;
  created_at?: string | null;
  finished_at?: string | null;
  note?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: isForm
      ? (init?.headers ?? {})
      : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body.slice(0, 300)}`);
  }
  return res.json() as Promise<T>;
}

function mappingPayload(mapping?: FieldMapping): string | undefined {
  if (!mapping) return undefined;
  const out: Record<string, string> = {};
  let any = false;
  for (const [key, value] of Object.entries(mapping)) {
    if (value === undefined) continue; // undefined => "__auto__" (let the backend detect)
    out[key] = value === null ? "__none__" : value; // null => explicitly no column
    any = true;
  }
  return any ? JSON.stringify(out) : undefined;
}

function fileForm(file: File, mapping?: FieldMapping, source?: string): FormData {
  const fd = new FormData();
  fd.append("file", file);
  const mp = mappingPayload(mapping);
  if (mp) fd.append("field_mapping", mp);
  if (source) fd.append("source", source);
  return fd;
}

export interface AnalyzeResponse {
  report: ReportDetail | null;
  analysis: AnalysisResult;
  stored: boolean;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),

  analyzeReport: (body: {
    report_text: string;
    report_type?: string;
    site?: string;
    activity?: string;
    date?: string;
    store?: boolean;
  }) =>
    request<AnalyzeResponse>("/api/reports/analyze", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  createReport: (body: {
    report_text: string;
    report_type?: string;
    site?: string;
    activity?: string;
    date?: string;
  }) =>
    request<ReportDetail>("/api/reports", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getReports: (params?: Record<string, string>) => {
    const qs = new URLSearchParams(params ?? {}).toString();
    return request<ReportDetail[]>(`/api/reports${qs ? `?${qs}` : ""}`);
  },

  getReport: (id: number | string) =>
    request<ReportDetail>(`/api/reports/${id}`),

  reviewReport: (
    id: number | string,
    body: {
      reviewer?: string;
      decision?: "confirmed" | "rejected" | "edited";
      corrected_priority?: Priority;
      corrected_rule?: string;
      comments?: string;
      mark_reviewed?: boolean;
    }
  ) =>
    request<{ ok: boolean; report: ReportDetail; decision: string | null }>(
      `/api/reports/${id}/review`,
      { method: "PATCH", body: JSON.stringify(body) }
    ),

  getOverview: () => request<AnalyticsOverview>("/api/analytics/overview"),

  /** Lightweight aggregate counts (HSE Review badge / reviewer workspace). */
  getReportCounts: () =>
    request<{
      total: number;
      pending: number;
      verified: number;
      rejected: number;
      failed: number;
    }>("/api/reports/counts"),
  getLifeSavingRules: () =>
    request<{ rules: RuleStat[]; sif_total: number; note?: string }>(
      "/api/analytics/life-saving-rules"
    ),
  getSites: () =>
    request<{ sites: SiteStat[]; note?: string }>("/api/analytics/sites"),
  getActivities: () =>
    request<{ activities: ActivityStat[]; note?: string }>(
      "/api/analytics/activities"
    ),
  getBarriers: () =>
    request<{ barriers: BarrierStat[]; note?: string }>(
      "/api/analytics/barriers"
    ),
  getPatterns: () => request<PatternResponse>("/api/analytics/patterns"),

  // Evaluation harness (golden labeled set — deterministic, no LLM).
  getEvaluation: (fresh = false) =>
    request<EvaluationReport>(`/api/evaluation${fresh ? "?fresh=true" : ""}`),

  // Human-in-the-loop feedback + training.
  getFeedbackSummary: () => request<FeedbackSummary>("/api/feedback/summary"),
  trainOnFeedback: () =>
    request<TrainResponse>("/api/feedback/train", {
      method: "POST",
    }),

  reanalyzeReport: (id: number | string) =>
    request<ReportDetail>(`/api/reports/${id}/reanalyze`, {
      method: "POST",
    }),

  ingestPreviewFile: (file: File, mapping?: FieldMapping) =>
    request<IngestPreview>("/api/ingest/file/preview", {
      method: "POST",
      body: fileForm(file, mapping),
    }),

  ingestImportFile: (file: File, mapping?: FieldMapping, source?: string) =>
    request<IngestJobStart>("/api/ingest/file", {
      method: "POST",
      body: fileForm(file, mapping, source),
    }),

  ingestRows: (rows: Record<string, unknown>[], mapping?: FieldMapping, source?: string) =>
    request<IngestJobStart>("/api/ingest/rows", {
      method: "POST",
      body: JSON.stringify({
        rows,
        field_mapping: mappingPayload(mapping),
        source,
      }),
    }),

  getIngestJob: (jobId: number) =>
    request<IngestJobState>(`/api/ingest/jobs/${jobId}`),

  listIngestJobs: () =>
    request<IngestJobState[]>("/api/ingest/jobs"),
};