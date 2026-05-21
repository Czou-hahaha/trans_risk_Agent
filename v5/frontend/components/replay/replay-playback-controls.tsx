"use client";

import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  currentIndex: number;
  totalEvents: number;
  isPlaying: boolean;
  onPlay: () => void;
  onPause: () => void;
  onStepForward: () => void;
  onStepBackward: () => void;
};

export function ReplayPlaybackControls({
  currentIndex,
  totalEvents,
  isPlaying,
  onPlay,
  onPause,
  onStepForward,
  onStepBackward,
}: Props) {
  const atStart = currentIndex <= 0;
  const atEnd = currentIndex >= totalEvents - 1;

  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="replay-step-controls">
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={onStepBackward}
          disabled={atStart}
          aria-label="Step backward"
        >
          <SkipBack className="h-4 w-4" />
        </Button>
        {isPlaying ? (
          <Button variant="default" size="sm" onClick={onPause} aria-label="Pause">
            <Pause className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            variant="default"
            size="sm"
            onClick={onPlay}
            disabled={atEnd}
            aria-label="Play"
          >
            <Play className="h-4 w-4" />
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={onStepForward}
          disabled={atEnd}
          aria-label="Step forward"
        >
          <SkipForward className="h-4 w-4" />
        </Button>
      </div>
      <p className="text-sm text-slate-600">
        Event {Math.min(currentIndex + 1, totalEvents)} / {totalEvents}
      </p>
    </div>
  );
}
