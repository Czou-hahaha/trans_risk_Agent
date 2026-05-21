"use client";

import { cn } from "@/lib/utils";
import type { ReplayTimelineEvent } from "@/lib/api";

const KIND_LABELS: Record<string, string> = {
  workflow_started: "Workflow Start",
  skill_started: "Skill Start",
  skill_completed: "Skill Complete",
  skill_skipped: "Skill Skipped",
  skill_failed: "Skill Failed",
  finding_discovered: "Finding",
  workflow_completed: "Workflow Done",
  report_generated: "Report",
};

const CATEGORY_COLORS: Record<string, string> = {
  workflow: "border-violet-300 bg-violet-50",
  skill: "border-blue-300 bg-blue-50",
  finding: "border-amber-300 bg-amber-50",
  report: "border-emerald-300 bg-emerald-50",
};

export function ReplayTimeline({
  events,
  currentIndex,
  onSelect,
}: {
  events: ReplayTimelineEvent[];
  currentIndex: number;
  onSelect: (index: number) => void;
}) {
  return (
    <div
      className="space-y-1 max-h-[50vh] overflow-y-auto pr-1"
      data-testid="replay-timeline-playback"
    >
      {events.map((ev, idx) => {
        const active = idx === currentIndex;
        const past = idx < currentIndex;
        return (
          <button
            key={ev.event_id}
            type="button"
            onClick={() => onSelect(idx)}
            className={cn(
              "w-full rounded-lg border-l-4 p-3 text-left text-sm transition-colors",
              CATEGORY_COLORS[ev.category] ?? "border-slate-200 bg-white",
              active && "ring-2 ring-blue-400",
              past && !active && "opacity-70"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-slate-900">
                {KIND_LABELS[ev.event_kind] ?? ev.event_kind}
              </span>
              <span className="text-xs text-slate-500 shrink-0">
                {new Date(ev.timestamp).toLocaleTimeString()}
              </span>
            </div>
            {ev.skill_name && (
              <p className="mt-0.5 text-xs text-slate-600">{ev.skill_name}</p>
            )}
            <p className="mt-1 text-xs text-slate-700 line-clamp-2">
              {ev.summary || ev.title}
            </p>
          </button>
        );
      })}
    </div>
  );
}
