"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getInvestigation,
  getInvestigationReport,
  type Investigation,
  type Report,
} from "@/lib/api";
import { WorkflowTimeline } from "@/components/investigation/workflow-timeline";
import { FindingsWorkspace } from "@/components/investigation/findings-workspace";
import { EvidencePanel } from "@/components/investigation/evidence-panel";
import { ReportPreview } from "@/components/investigation/report-preview";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

const POLL_MS = 2000;

export default function InvestigationWorkspaceDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [inv, setInv] = useState<Investigation | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [selectedStep, setSelectedStep] = useState("metric_monitor");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getInvestigation(id);
      setInv({ ...data, report_payload: data.report_payload });
      setError(null);
      if (data.report_id && data.status === "completed") {
        try {
          const r = await getInvestigationReport(id);
          setReport(r);
          setInv((prev) =>
            prev
              ? {
                  ...prev,
                  executive_summary: r.executive_summary,
                  report_payload: r as unknown as Record<string, unknown>,
                }
              : prev
          );
        } catch {
          /* report not ready */
        }
      }
      if (data.steps?.length) {
        const running = data.steps.find((s) => s.status === "running");
        if (running) setSelectedStep(running.step_name);
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
    return <div className="p-8 text-slate-500">Loading investigation workspace…</div>;
  }

  const step = inv.steps?.find((s) => s.step_name === selectedStep);
  const invWithReport = {
    ...inv,
    report_payload: (report as unknown as Record<string, unknown>) ?? inv.report_payload,
  };

  return (
    <div className="flex h-[calc(100vh)] flex-col bg-surface-muted">
      <header className="border-b border-surface-border bg-white px-6 py-4 shrink-0">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <Link
              href="/investigation"
              className="text-xs text-slate-500 hover:text-slate-800"
            >
              ← Workspace
            </Link>
            <h1 className="text-lg font-semibold text-slate-900 truncate mt-1">
              {inv.goal}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              {inv.metric_name.toUpperCase()}
              {inv.analysis_date && ` · ${inv.analysis_date}`}
              {inv.executed_skills?.length
                ? ` · ${inv.executed_skills.length} skills`
                : ""}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge status={inv.status} />
            <Button variant="ghost" size="sm" onClick={() => load()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {inv.executive_summary && (
          <p className="mt-3 text-sm text-slate-700 leading-relaxed border-l-2 border-blue-400 pl-3">
            {inv.executive_summary}
          </p>
        )}
        {inv.error_message && (
          <p className="mt-2 text-sm text-red-600">
            Failed at {inv.failed_stage}: {inv.error_message}
          </p>
        )}
      </header>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <aside className="w-72 shrink-0 border-r border-surface-border bg-white p-4 overflow-y-auto">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
            Investigation Timeline
          </h2>
          {inv.steps && (
            <WorkflowTimeline
              steps={inv.steps}
              selectedStep={selectedStep}
              onSelect={setSelectedStep}
            />
          )}
        </aside>

        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <div className="flex flex-1 min-h-0 overflow-hidden">
            <section className="flex-1 overflow-y-auto p-4">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
                Findings Workspace
              </h2>
              <FindingsWorkspace inv={invWithReport} />
            </section>
            <aside className="w-96 shrink-0 border-l border-surface-border bg-white p-4 overflow-y-auto hidden lg:block">
              <EvidencePanel step={step} />
            </aside>
          </div>

          <footer className="shrink-0 border-t border-surface-border bg-white max-h-[35vh] overflow-y-auto">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 px-4 pt-3">
              Investigation Report Preview
            </h2>
            <ReportPreview
              executiveSummary={inv.executive_summary ?? report?.executive_summary}
              markdown={report?.markdown_export}
              loading={inv.status === "running"}
            />
          </footer>
        </main>
      </div>
    </div>
  );
}
