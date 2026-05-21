"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getInvestigationReplay,
  type InvestigationReplay,
} from "@/lib/api";
import { ReplayPlaybackControls } from "@/components/replay/replay-playback-controls";
import { ReplayTimeline } from "@/components/replay/replay-timeline";
import {
  ReplayCurrentEventPanel,
  ReplayFindingsPanel,
  ReplayReportPanel,
  ReplayWorkflowPanel,
} from "@/components/replay/replay-panels";
import { useReplayPlayback } from "@/hooks/use-replay-playback";
import { StatusBadge } from "@/components/ui/badge";
import { History } from "lucide-react";

export default function InvestigationReplayPage() {
  const params = useParams();
  const id = params.id as string;
  const [replay, setReplay] = useState<InvestigationReplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const total = replay?.events.length ?? 0;
  const {
    currentIndex,
    isPlaying,
    play,
    pause,
    stepForward,
    stepBackward,
    seek,
  } = useReplayPlayback(total);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getInvestigationReplay(id);
      setReplay(data);
      setError(null);
    } catch (e) {
      setReplay(null);
      setError(e instanceof Error ? e.message : "Failed to load replay");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !replay) {
    return (
      <div className="p-8 text-slate-500 flex items-center gap-2">
        <History className="h-5 w-5 animate-pulse" />
        Loading investigation replay…
      </div>
    );
  }

  if (error && !replay) {
    return (
      <div className="p-8">
        <p className="text-red-600">{error}</p>
        <Link href={`/investigation/${id}`} className="mt-4 inline-block text-sm text-blue-600">
          ← Back to investigation
        </Link>
      </div>
    );
  }

  if (!replay) return null;

  const currentEvent = replay.events[currentIndex] ?? null;
  const progress =
    total > 1 ? Math.round((currentIndex / (total - 1)) * 100) : 100;

  return (
    <div className="flex h-[calc(100vh)] flex-col bg-surface-muted" data-testid="page-replay">
      <header className="border-b border-surface-border bg-white px-6 py-4 shrink-0">
        <Link
          href={`/investigation/${id}`}
          className="text-xs text-slate-500 hover:text-slate-800"
        >
          ← Investigation workspace
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <History className="h-5 w-5 text-violet-600" />
              Investigation Replay
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {replay.goal} · {replay.metric_name.toUpperCase()}
            </p>
          </div>
          <StatusBadge status={replay.status} />
        </div>

        <div className="mt-4">
          <ReplayPlaybackControls
            currentIndex={currentIndex}
            totalEvents={total}
            isPlaying={isPlaying}
            onPlay={play}
            onPause={pause}
            onStepForward={stepForward}
            onStepBackward={stepBackward}
          />
        </div>
        <div className="mt-3 h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
          <div
            className="h-full bg-violet-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </header>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <aside className="w-80 shrink-0 border-r border-surface-border bg-white p-4 overflow-hidden flex flex-col">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3 shrink-0">
            Timeline Playback
          </h2>
          <ReplayTimeline
            events={replay.events}
            currentIndex={currentIndex}
            onSelect={seek}
          />
        </aside>

        <main className="flex-1 overflow-y-auto p-6 space-y-4">
          <ReplayCurrentEventPanel event={currentEvent} />
          <div className="grid gap-4 lg:grid-cols-2">
            <ReplayWorkflowPanel
              events={replay.events}
              currentIndex={currentIndex}
              executedSkills={replay.executed_skills}
            />
            <ReplayFindingsPanel
              events={replay.events}
              currentIndex={currentIndex}
            />
          </div>
          <ReplayReportPanel
            events={replay.events}
            currentIndex={currentIndex}
          />
        </main>
      </div>
    </div>
  );
}
