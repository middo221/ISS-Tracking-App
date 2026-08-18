import { useEffect, useRef, useState } from 'react';

import { ApiError, fetchPosition, isAbortError } from '../api/issClient';
import type { Position } from '../types/iss';
import { useNow } from './useNow';

export const POLL_INTERVAL_MS = 3_000;
export const BACKOFF_INTERVAL_MS = 15_000;
export const FAILURES_BEFORE_BACKOFF = 3;

/** Past this gap the readout is showing a position we can no longer vouch for. */
const STALE_AFTER_MS = 12_000;

interface Snapshot {
  current: Position;
  previous: Position | null;
  receivedAt: number;
}

export interface IssPositionState {
  data: Position | null;
  previous: Position | null;
  error: string | null;
  isStale: boolean;
  isBackingOff: boolean;
  secondsSinceContact: number | null;
  pollIntervalMs: number;
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return 'Lost contact with the tracking service';
}

export function useIssPosition(): IssPositionState {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failures, setFailures] = useState(0);
  const nowMs = useNow();

  const failuresRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let inFlight: AbortController | null = null;

    const poll = async (): Promise<void> => {
      // A fresh controller per poll, so a slow request can be dropped on unmount without
      // taking the polling loop with it.
      inFlight = new AbortController();
      try {
        const position = await fetchPosition(inFlight.signal);
        if (cancelled) return;

        failuresRef.current = 0;
        setFailures(0);
        setError(null);
        setSnapshot((previous) => ({
          current: position,
          previous: previous?.current ?? null,
          receivedAt: Date.now(),
        }));
      } catch (caught) {
        if (cancelled || isAbortError(caught)) return;

        failuresRef.current += 1;
        setFailures(failuresRef.current);
        setError(describe(caught));
      } finally {
        if (!cancelled) {
          const backingOff = failuresRef.current >= FAILURES_BEFORE_BACKOFF;
          timer = window.setTimeout(
            () => void poll(),
            backingOff ? BACKOFF_INTERVAL_MS : POLL_INTERVAL_MS,
          );
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      inFlight?.abort();
    };
  }, []);

  const isBackingOff = failures >= FAILURES_BEFORE_BACKOFF;

  return {
    data: snapshot?.current ?? null,
    previous: snapshot?.previous ?? null,
    error,
    isStale: snapshot !== null && nowMs - snapshot.receivedAt > STALE_AFTER_MS,
    isBackingOff,
    secondsSinceContact:
      snapshot === null ? null : Math.max(0, Math.round((nowMs - snapshot.receivedAt) / 1000)),
    pollIntervalMs: isBackingOff ? BACKOFF_INTERVAL_MS : POLL_INTERVAL_MS,
  };
}
