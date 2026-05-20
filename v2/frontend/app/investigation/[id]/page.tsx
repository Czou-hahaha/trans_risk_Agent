"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getInvestigation, type Investigation } from "@/lib/api";
import { WorkflowTimeline } from "@/components/investigation/workflow-timeline";
import { StepDetail } from "@/components/investigation/step-detail";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, RefreshCw } from "lucide-react";

const POLL_MS = 2000;

export default function InvestigationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [inv, setInv] = useState<Investigation | null>(null);
  const [selectedStep, setSelectedStep] = useState("monitor");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getInvestigation(id);
      setInv(data);
      setError(null);
      if (data.status === "completed" && data.steps?.length) {
        const last = [...data.steps].sort((a, b) => b.step_order - a.step_order)[0];
        if (last?.status === "completed") setSelectedStep(last.step_name);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!inv || (inv.status !== "running" && inv.status !== "pending")) return;
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [inv?.status, load]);

  if (error && !inv) {
    return <div className="p-8 text-red-600">{error}</div>;
  }
  if (!inv) {
    return <div className="p-8 text-slate-500">Loading investigation…</div>;
  }

  const step = inv.steps?.find((s) => s.step_name === selectedStep);

  return (
    <div className="flex h-[calc(100vh)] flex-col">
      <header className="border-b border-surface-border bg-white px-8 py-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-slate-900 truncate">
              {inv.goal}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {inv.metric_name.toUpperCase()} · Workflow {inv.workflow_id.slice(0, 8)}…
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge status={inv.status} />
            <Button variant="ghost" size="sm" onClick={() => load()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            {inv.report_id && (
              <Link href={`/reports/${inv.report_id}`}>
                <Button variant="secondary" size="sm">
                  <FileText className="mr-2 h-4 w-4" />
                  View Report
                </Button>
              </Link>
            )}
          </div>
        </div>
        {inv.error_message && (
          <p className="mt-3 text-sm text-red-600">
            Failed at {inv.failed_stage}: {inv.error_message}
          </p>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 shrink-0 border-r border-surface-border bg-white p-6 overflow-y-auto">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-4">
            Workflow Timeline
          </h2>
          {inv.steps && (
            <WorkflowTimeline
              steps={inv.steps}
              selectedStep={selectedStep}
              onSelect={setSelectedStep}
            />
          )}
        </aside>
        <section className="flex-1 overflow-y-auto p-6 bg-surface-muted">
          <StepDetail step={step} />
        </section>
      </div>
    </div>
  );
}
