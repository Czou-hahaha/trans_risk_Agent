"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ChartProps = {
  stepJson: Record<string, unknown> | null | undefined;
  stepName: string;
};

export function InvestigationCharts({ stepJson, stepName }: ChartProps) {
  if (!stepJson) {
    return <p className="text-sm text-slate-500">Select a completed step for evidence charts.</p>;
  }

  if (stepName === "trend_analysis" || stepName === "metric_monitor") {
    const evidence = (stepJson.evidence || stepJson) as Record<string, unknown>;
    const labels = (evidence.period_labels as string[]) || [];
    const values = (evidence.values as number[]) || [];
    if (!labels.length) return <p className="text-sm text-slate-500">No time series in evidence.</p>;
    const data = labels.map((label, i) => ({
      label,
      value: Number((values[i] ?? 0) * 100).toFixed(2)),
    }));
    return (
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} unit="%" />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (stepName === "dimension_contribution") {
    const rows =
      (stepJson.top_contributors as { dimension_value: string; contribution_pp: number }[]) ||
      [];
    const data = rows.slice(0, 8).map((r) => ({
      name: r.dimension_value,
      contribution: Number(r.contribution_pp),
    }));
    if (!data.length) return <p className="text-sm text-slate-500">No contribution data.</p>;
    return (
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fontSize: 10 }} unit="pp" />
          <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey="contribution" fill="#6366f1" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (stepName === "segment_stability") {
    const segs =
      (stepJson.top_unstable_segments as {
        dimension_value: string;
        volatility_score: number;
        stability_score: number;
      }[]) || [];
    const data = segs.slice(0, 6).map((s) => ({
      name: s.dimension_value,
      volatility: Number((s.volatility_score * 100).toFixed(1)),
      stability: Number((s.stability_score * 100).toFixed(1)),
    }));
    if (!data.length) return <p className="text-sm text-slate-500">No segment data.</p>;
    return (
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="volatility" fill="#f59e0b" />
          <Bar dataKey="stability" fill="#10b981" />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (stepName === "strategy_impact") {
    const findings = (stepJson.findings as Record<string, unknown>[]) || [];
    const f = findings[0];
    if (!f) return <p className="text-sm text-slate-500">No strategy finding.</p>;
    const data = [
      { metric: "FPD7", before: Number(f.fpd7_before) * 100, after: Number(f.fpd7_after) * 100 },
      {
        metric: "Approval",
        before: Number(f.approval_rate_before) * 100,
        after: Number(f.approval_rate_after) * 100,
      },
    ];
    return (
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="metric" />
          <YAxis unit="%" tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="before" fill="#94a3b8" name="Before" />
          <Bar dataKey="after" fill="#2563eb" name="After" />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return <p className="text-sm text-slate-500">Charts not available for this step.</p>;
}
