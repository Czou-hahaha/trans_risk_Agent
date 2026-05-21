"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const DEFAULT_INTERVAL_MS = 1200;

export function useReplayPlayback(totalEvents: number, intervalMs = DEFAULT_INTERVAL_MS) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const pause = useCallback(() => {
    setIsPlaying(false);
    clearTimer();
  }, [clearTimer]);

  const play = useCallback(() => {
    if (totalEvents <= 0) return;
    if (currentIndex >= totalEvents - 1) {
      setCurrentIndex(0);
    }
    setIsPlaying(true);
  }, [currentIndex, totalEvents]);

  const stepForward = useCallback(() => {
    pause();
    setCurrentIndex((i) => Math.min(i + 1, Math.max(0, totalEvents - 1)));
  }, [pause, totalEvents]);

  const stepBackward = useCallback(() => {
    pause();
    setCurrentIndex((i) => Math.max(i - 1, 0));
  }, [pause]);

  const seek = useCallback(
    (index: number) => {
      pause();
      setCurrentIndex(Math.max(0, Math.min(index, Math.max(0, totalEvents - 1))));
    },
    [pause, totalEvents]
  );

  useEffect(() => {
    if (!isPlaying || totalEvents <= 0) return;
    clearTimer();
    timerRef.current = setInterval(() => {
      setCurrentIndex((i) => {
        if (i >= totalEvents - 1) {
          setIsPlaying(false);
          clearTimer();
          return i;
        }
        return i + 1;
      });
    }, intervalMs);
    return clearTimer;
  }, [isPlaying, totalEvents, intervalMs, clearTimer]);

  useEffect(() => {
    setCurrentIndex(0);
    setIsPlaying(false);
    clearTimer();
  }, [totalEvents, clearTimer]);

  return {
    currentIndex,
    isPlaying,
    play,
    pause,
    stepForward,
    stepBackward,
    seek,
  };
}
