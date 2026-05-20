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
  workflow_id: string;
  status: string;
  needs_investigation: boolean | null;
  error_message?: string | null;
  failed_stage?: string | null;
  created_at: string;
  updated_at: string;
  steps?: InvestigationStep[];
  report_id?: string | null;
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

export function createInvestigation(goal: string, metric_name?: string) {
  return fetchJson<Investigation>("/api/investigations", {
    method: "POST",
    body: JSON.stringify({ goal, metric_name }),
  });
}

export function getReport(id: string) {
  return fetchJson<Report>(`/api/reports/${id}`);
}
