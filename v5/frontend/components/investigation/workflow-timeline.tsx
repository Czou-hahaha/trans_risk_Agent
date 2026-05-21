"use client";

import { CheckCircle2, Circle, Loader2, XCircle, MinusCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { InvestigationStep } from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  metric_monitor: "Metric Monitor",
  monitor: "Metric Monitor",
  trend_analysis: "Trend Analysis",
  dimension_contribution: "Dimension Contribution",
  contribution: "Dimension Contribution",
  segment_stability: "Segment Stability",
  strategy_impact: "Strategy Impact",
  finding_summary: "Finding Summary",
  summary: "Finding Summary",
  report_builder: "Report Builder",
  report: "Report Builder",
};

function StepIcon({ status }: { status: string }) {
  if (status === "completed")
    return <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />;
  if (status === "running")
    return <Loader2 className="h-5 w-5 text-amber-500 animate-spin shrink-0" />;
  if (status === "failed")
    return <XCircle className="h-5 w-5 text-red-500 shrink-0" />;
  if (status === "skipped")
    return <MinusCircle className="h-5 w-5 text-slate-400 shrink-0" />;
  return <Circle className="h-5 w-5 text-slate-300 shrink-0" />;
}

export function WorkflowTimeline({
  steps,
  selectedStep,
  onSelect,
}: {
  steps: InvestigationStep[];
  selectedStep: string;
  onSelect: (name: string) => void;
}) {
  const ordered = [...steps].sort((a, b) => a.step_order - b.step_order);

  return (
    <div className="space-y-0" data-testid="workspace-timeline" data-timeline-ordered="true">
      {ordered.map((step, idx) => {
        const active = selectedStep === step.step_name;
        const isLast = idx === ordered.length - 1;
        return (
          <div key={step.id} className="relative">
            {!isLast && (
              <div
                className={cn(
                  "absolute left-[9px] top-8 h-[calc(100%-8px)] w-0.5",
                  step.status === "completed" ? "bg-emerald-200" : "bg-slate-200"
                )}
              />
            )}
            <button
              type="button"
              data-testid={`timeline-step-${step.status}`}
              data-step-order={step.step_order}
              onClick={() => onSelect(step.step_name)}
              className={cn(
                "relative w-full rounded-lg p-3 text-left transition-colors",
                active ? "bg-blue-50 ring-1 ring-blue-200" : "hover:bg-surface-muted"
              )}
            >
              <div className="flex gap-3">
                <StepIcon status={step.status} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-900">
                    {STEP_LABELS[step.step_name] || step.step_name}
                  </p>
                  <p className="mt-0.5 text-xs capitalize text-slate-500">
                    {step.status}
                    {step.completed_at &&
                      ` · ${new Date(step.completed_at).toLocaleTimeString()}`}
                  </p>
                  {step.output_preview && (
                    <p className="mt-2 text-xs text-slate-600 leading-relaxed line-clamp-2">
                      {step.output_preview}
                    </p>
                  )}
                </div>
              </div>
            </button>
          </div>
        );
      })}
    </div>
  );
}
