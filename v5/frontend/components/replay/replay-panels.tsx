"use client";

import type { ReplayTimelineEvent } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function visibleEvents(events: ReplayTimelineEvent[], index: number) {
  return events.slice(0, index + 1);
}

export function ReplayWorkflowPanel({
  events,
  currentIndex,
  executedSkills,
}: {
  events: ReplayTimelineEvent[];
  currentIndex: number;
  executedSkills: string[];
}) {
  const visible = visibleEvents(events, currentIndex);
  const skillStates = new Map<string, string>();
  for (const ev of visible) {
    if (ev.category !== "skill" || !ev.skill_name) continue;
    if (ev.event_kind === "skill_started") skillStates.set(ev.skill_name, "running");
    if (ev.event_kind === "skill_completed") skillStates.set(ev.skill_name, "completed");
    if (ev.event_kind === "skill_skipped") skillStates.set(ev.skill_name, "skipped");
    if (ev.event_kind === "skill_failed") skillStates.set(ev.skill_name, "failed");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Workflow Progression</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          {executedSkills.map((skill) => {
            const status = skillStates.get(skill) ?? "pending";
            return (
              <li
                key={skill}
                className="flex items-center justify-between rounded-md border border-surface-border px-3 py-2"
              >
                <span className="font-medium text-slate-800">{skill}</span>
                <span className="text-xs capitalize text-slate-500">{status}</span>
              </li>
            );
          })}
        </ul>
        {visible.find((e) => e.event_kind === "workflow_started") && (
          <p className="mt-3 text-xs text-slate-600">
            {visible.find((e) => e.event_kind === "workflow_started")?.summary}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function ReplayFindingsPanel({
  events,
  currentIndex,
}: {
  events: ReplayTimelineEvent[];
  currentIndex: number;
}) {
  const findings = visibleEvents(events, currentIndex).filter(
    (e) => e.event_kind === "finding_discovered"
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Findings Evolution</CardTitle>
      </CardHeader>
      <CardContent>
        {findings.length === 0 ? (
          <p className="text-sm text-slate-500">No findings yet at this step.</p>
        ) : (
          <ul className="space-y-3">
            {findings.map((ev) => (
              <li
                key={ev.event_id}
                className="rounded-md border border-amber-100 bg-amber-50/50 px-3 py-2"
              >
                <p className="text-xs font-medium text-amber-900">
                  {ev.skill_name ?? "finding"}
                </p>
                <p className="mt-1 text-sm text-slate-700">{ev.summary}</p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function ReplayReportPanel({
  events,
  currentIndex,
}: {
  events: ReplayTimelineEvent[];
  currentIndex: number;
}) {
  const visible = visibleEvents(events, currentIndex);
  const reportEv = [...visible]
    .reverse()
    .find((e) => e.event_kind === "report_generated");

  return (
    <Card data-testid="replay-report-panel">
      <CardHeader>
        <CardTitle className="text-base">Report Generation</CardTitle>
      </CardHeader>
      <CardContent>
        {!reportEv ? (
          <p className="text-sm text-slate-500">
            Report not generated yet — step forward through the workflow.
          </p>
        ) : (
          <div className="text-sm text-slate-700 space-y-2">
            <p className="leading-relaxed">{reportEv.summary}</p>
            {typeof reportEv.payload.executive_summary === "string" &&
              reportEv.payload.executive_summary !== reportEv.summary && (
                <p className="text-xs text-slate-500 border-t pt-2">
                  {reportEv.payload.executive_summary as string}
                </p>
              )}
            {typeof reportEv.payload.finding_count === "number" && (
              <p className="text-xs text-slate-500">
                Findings in report: {reportEv.payload.finding_count as number}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function ReplayCurrentEventPanel({
  event,
}: {
  event: ReplayTimelineEvent | null;
}) {
  if (!event) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-slate-500">Select an event.</CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardHeader>
        <CardTitle className="text-base">{event.title || event.event_kind}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate-700 space-y-2">
        <p>{event.summary}</p>
        <p className="text-xs text-slate-500">
          {event.category} · {new Date(event.timestamp).toLocaleString()}
          {event.duration_ms != null && ` · ${event.duration_ms}ms`}
        </p>
      </CardContent>
    </Card>
  );
}
