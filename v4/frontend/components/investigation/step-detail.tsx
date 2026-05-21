"use client";

import type { InvestigationStep } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function ContributionTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <p className="text-sm text-slate-500">No contributors.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-surface-border">
      <table className="w-full text-sm">
        <thead className="bg-surface-muted text-left text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">Rank</th>
            <th className="px-3 py-2">Dimension</th>
            <th className="px-3 py-2">Value</th>
            <th className="px-3 py-2">Contribution</th>
            <th className="px-3 py-2">Delta</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-surface-border">
              <td className="px-3 py-2">{String(r.rank ?? i + 1)}</td>
              <td className="px-3 py-2">{String(r.dimension_name)}</td>
              <td className="px-3 py-2 font-medium">{String(r.dimension_value)}</td>
              <td className="px-3 py-2 font-mono text-xs">
                {Number(r.contribution_pp).toFixed(2)}pp
              </td>
              <td className="px-3 py-2 font-mono text-xs">
                {Number(r.delta_pp).toFixed(2)}pp
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StepDetail({ step }: { step: InvestigationStep | undefined }) {
  if (!step) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-slate-500">
          Select a workflow step to view details.
        </CardContent>
      </Card>
    );
  }

  const data = step.output_json;

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base capitalize">
          {step.step_name} — Step Output
        </CardTitle>
        {step.output_preview && (
          <p className="mt-1 text-sm text-slate-600">{step.output_preview}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {step.step_name === "monitor" && data && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Metric label="Metric" value={String(data.metric_name)} />
            <Metric label="Severity" value={String(data.severity)} />
            <Metric
              label="Delta"
              value={`${Number(data.delta_pp) >= 0 ? "+" : ""}${Number(data.delta_pp).toFixed(2)}pp`}
            />
            <Metric
              label="Needs Investigation"
              value={data.needs_investigation ? "Yes" : "No"}
            />
            <div className="sm:col-span-2 rounded-lg bg-surface-muted p-3 text-sm text-slate-700">
              {String(data.summary || "")}
            </div>
          </div>
        )}

        {step.step_name === "contribution" && data && (
          <ContributionTable
            rows={(data.top_contributors as Record<string, unknown>[]) || []}
          />
        )}

        {step.step_name === "summary" && data && (
          <div className="space-y-4 text-sm">
            <section>
              <h4 className="font-semibold text-slate-900">Business Summary</h4>
              <p className="mt-1 text-slate-700 leading-relaxed">
                {String(data.business_summary)}
              </p>
            </section>
            <section>
              <h4 className="font-semibold text-slate-900">Risk Hypothesis</h4>
              <p className="mt-1 text-slate-700 leading-relaxed">
                {String(data.risk_hypothesis)}
              </p>
            </section>
            <section>
              <h4 className="font-semibold text-slate-900">Recommended Actions</h4>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
                {(data.recommended_actions as string[] | undefined)?.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </section>
          </div>
        )}

        {step.status === "pending" && (
          <p className="text-sm text-slate-500">Waiting for this stage to start…</p>
        )}
        {step.status === "skipped" && (
          <p className="text-sm text-slate-500">{step.output_preview}</p>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-border p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-medium text-slate-900">{value}</p>
    </div>
  );
}
