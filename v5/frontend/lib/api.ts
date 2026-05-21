/** Browser: same-origin /api (Next rewrite → backend). Server: direct backend URL. */
function resolveApiUrl(path: string): string {
  if (typeof window !== "undefined") {
    return path;
  }
  const base =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8001";
  return `${base.replace(/\/$/, "")}${path}`;
}

export type InvestigationStep = {
  id: string;
  step_name: string;
  step_order: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  output_preview: string | null;
  output_json: Record<string, unknown> | null;
};

export type Investigation = {
  id: string;
  goal: string;
  metric_name: string;
  analysis_date?: string | null;
  workflow_id: string;
  status: string;
  needs_investigation: boolean | null;
  error_message?: string | null;
  failed_stage?: string | null;
  created_at: string;
  updated_at: string;
  steps?: InvestigationStep[];
  report_id?: string | null;
  executive_summary?: string | null;
  executed_skills?: string[] | null;
  report_payload?: Record<string, unknown> | null;
};

export type DashboardData = {
  kpis: {
    total_investigations: number;
    running_investigations: number;
    completed_investigations: number;
    failed_investigations: number;
  };
  latest_investigations: Investigation[];
  latest_risk_alerts: {
    id: string;
    metric_name: string;
    summary: string;
    severity: string;
    created_at: string;
  }[];
  latest_reports: Investigation[];
};

export type Report = {
  id: string;
  investigation_id: string;
  goal: string;
  metric_name: string;
  workflow_status: string;
  business_summary: string;
  risk_hypothesis: string;
  recommended_actions: string[];
  contributor_ranking: {
    rank: number;
    dimension_name: string;
    dimension_value: string;
    contribution_pp: number;
    delta_pp: number;
  }[];
  monitor_finding: Record<string, unknown> | null;
  executive_summary?: string;
  executed_skills?: string[];
  timeline?: Record<string, unknown>[];
  generated_at: string;
  markdown_export: string;
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(resolveApiUrl(path), {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function getDashboard() {
  return fetchJson<DashboardData>("/api/investigations/dashboard");
}

export function listInvestigations(limit = 20) {
  return fetchJson<Investigation[]>(`/api/investigations?limit=${limit}`);
}

export function getInvestigation(id: string) {
  return fetchJson<Investigation>(`/api/investigations/${id}`);
}

export function createInvestigation(
  goal: string,
  metric_name?: string,
  analysis_date?: string
) {
  return fetchJson<Investigation>("/api/investigations", {
    method: "POST",
    body: JSON.stringify({ goal, metric_name, analysis_date }),
  });
}

export function runInvestigation(params: {
  metric_name: string;
  analysis_date: string;
  goal?: string;
}) {
  return fetchJson<Investigation>("/api/investigation/run", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getInvestigationReport(investigationId: string) {
  return fetchJson<Report>(`/api/investigation/${investigationId}/report`);
}

export type EvaluationResultItem = {
  evaluation_type: string;
  evaluation_score: number;
  detected_issues: string[];
  recommendations: string[];
  generated_at: string;
};

export type EvaluationMetrics = {
  workflow_quality: number;
  report_quality: number;
  finding_confidence: number;
  pattern_confidence: number;
  overall_score: number;
};

export type InvestigationEvaluation = {
  investigation_id: string;
  metrics: EvaluationMetrics;
  results: EvaluationResultItem[];
  generated_at: string;
};

export function getInvestigationEvaluation(investigationId: string) {
  return fetchJson<InvestigationEvaluation>(
    `/api/investigations/${investigationId}/evaluation`
  );
}

export type ReplayTimelineEvent = {
  event_id: string;
  sequence_index: number;
  timestamp: string;
  event_kind: string;
  category: string;
  skill_name?: string | null;
  execution_status?: string | null;
  title: string;
  summary: string;
  duration_ms?: number | null;
  payload: Record<string, unknown>;
};

export type InvestigationReplay = {
  investigation_id: string;
  workflow_id: string;
  metric_name: string;
  goal: string;
  workflow_status: string;
  status: string;
  total_events: number;
  events: ReplayTimelineEvent[];
  executed_skills: string[];
  generated_at?: string | null;
};

export function getInvestigationReplay(investigationId: string) {
  return fetchJson<InvestigationReplay>(
    `/api/investigations/${investigationId}/replay`
  );
}

export function getReport(id: string) {
  return fetchJson<Report>(`/api/reports/${id}`);
}

export type IntelligenceItem = {
  id: string;
  title: string;
  summary: string;
  metric_name?: string | null;
  dimension_name?: string | null;
  dimension_value?: string | null;
  occurrence_count: number;
  confidence_score: number;
  investigation_ids: string[];
  pattern_type?: string | null;
};

export type WeeklyHighlight = {
  category: string;
  headline: string;
  detail: string;
  severity: string;
};

export type WeeklyRiskSummary = {
  period_label: string;
  generated_at: string;
  headline: string;
  highlights: WeeklyHighlight[];
  investigation_count: number;
  pattern_count: number;
};

export type TrendIntelligence = {
  risk_trend_shifts: IntelligenceItem[];
  approval_trend_shifts: IntelligenceItem[];
  volume_risk_tradeoffs: IntelligenceItem[];
};

export type PatternIntelligence = {
  recurring_patterns: IntelligenceItem[];
  historical_recurrence: IntelligenceItem[];
  cross_investigation_signals: IntelligenceItem[];
};

export type ExecutiveIntelligence = {
  generated_at: string;
  window_days: number;
  data_available: boolean;
  message?: string | null;
  top_recurring_contributors: IntelligenceItem[];
  most_unstable_segments: IntelligenceItem[];
  highest_risk_strategies: IntelligenceItem[];
  recurring_deterioration_patterns: IntelligenceItem[];
  weekly_summary: WeeklyRiskSummary;
  trend_intelligence: TrendIntelligence;
  pattern_intelligence: PatternIntelligence;
};

export function getExecutiveIntelligence(weeklyDays = 7, patternDays = 30) {
  return fetchJson<ExecutiveIntelligence>(
    `/api/intelligence/executive?weekly_days=${weeklyDays}&pattern_days=${patternDays}`
  );
}
