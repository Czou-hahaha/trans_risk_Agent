"use client";

import type { Investigation } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";

type Contributor = {
  dimension_name?: string;
  dimension_value?: string;
  contribution_pp?: number;
  delta_pp?: number;
  rank?: number;
};

type Segment = {
  dimension_value?: string;
  segment_health?: string;
  stability_score?: number;
  volatility_level?: string;
};

export function FindingsWorkspace({ inv }: { inv: Investigation }) {
  const report = inv.report_payload;
  const contributors: Contributor[] =
    report?.contribution_findings ??
    (inv.steps?.find((s) => s.step_name === "dimension_contribution")?.output_json
      ?.top_contributors as Contributor[]) ??
    [];

  const segments: Segment[] =
    report?.segment_stability_result?.top_unstable_segments ??
    (inv.steps?.find((s) => s.step_name === "segment_stability")?.output_json
      ?.top_unstable_segments as Segment[]) ??
    [];

  const trendStep = inv.steps?.find((s) => s.step_name === "trend_analysis")?.output_json;
  const trend =
    (report?.trend_result as { trend_finding?: Record<string, unknown> })?.trend_finding ??
    (trendStep as { trend_finding?: Record<string, unknown> })?.trend_finding ??
    trendStep;

  const strategy =
    report?.strategy_impact_result?.findings?.[0] ??
    inv.steps?.find((s) => s.step_name === "strategy_impact")?.output_json?.findings?.[0];

  return (
    <div className="grid gap-4 md:grid-cols-2" data-testid="workspace-findings">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Trend Deterioration</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-700">
          {trend ? (
            <ul className="space-y-1">
              <li>
                Direction: <strong>{String(trend.trend_direction)}</strong>
              </li>
              <li>
                Rolling change:{" "}
                <strong>{Number(trend.rolling_change_pp).toFixed(2)}pp</strong>
              </li>
              <li className="text-slate-600">{String(trend.summary)}</li>
            </ul>
          ) : (
            <p className="text-slate-500">No trend finding.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Contributors</CardTitle>
        </CardHeader>
        <CardContent>
          {contributors.length ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="pb-2">Segment</th>
                  <th className="pb-2">Contrib.</th>
                  <th className="pb-2">Delta</th>
                </tr>
              </thead>
              <tbody>
                {contributors.slice(0, 5).map((c, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2 font-medium">
                      {c.dimension_value}
                      <span className="text-slate-400 text-xs ml-1">
                        ({c.dimension_name})
                      </span>
                    </td>
                    <td className="py-2">
                      {Number(c.contribution_pp).toFixed(2)}pp
                    </td>
                    <td className="py-2">{Number(c.delta_pp).toFixed(2)}pp</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-slate-500">No contributors.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Unstable Segments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {segments.length ? (
            segments.slice(0, 5).map((s, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"
              >
                <span className="font-medium">{s.dimension_value}</span>
                <StatusBadge status={s.segment_health || "watchlist"} />
              </div>
            ))
          ) : (
            <p className="text-slate-500">No unstable segments flagged.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Strategy Effectiveness</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-700">
          {strategy ? (
            <ul className="space-y-1">
              <li>
                Strategy: <strong>{strategy.strategy_name}</strong>
              </li>
              <li>
                Effectiveness:{" "}
                <StatusBadge status={strategy.strategy_effectiveness} />
              </li>
              <li>FPD7: {Number(strategy.fpd7_delta_pp).toFixed(2)}pp</li>
              <li>Approval: {Number(strategy.approval_delta_pp).toFixed(2)}pp</li>
            </ul>
          ) : (
            <p className="text-slate-500">No strategy impact analysis.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
