"use client";

import type { InvestigationStep } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InvestigationCharts } from "./investigation-charts";

export function EvidencePanel({ step }: { step?: InvestigationStep }) {
  return (
    <Card className="h-full border-surface-border shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Evidence Panel</CardTitle>
        <p className="text-xs text-slate-500">
          {step ? step.step_name.replace(/_/g, " ") : "Select a workflow step"}
        </p>
      </CardHeader>
      <CardContent>
        <InvestigationCharts
          stepJson={step?.output_json ?? undefined}
          stepName={step?.step_name ?? ""}
        />
        {step?.output_json && (
          <details className="mt-4">
            <summary className="text-xs font-medium text-slate-500 cursor-pointer">
              Raw evidence JSON
            </summary>
            <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-900 text-slate-100 p-3 text-[10px]">
              {JSON.stringify(step.output_json, null, 2)}
            </pre>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
