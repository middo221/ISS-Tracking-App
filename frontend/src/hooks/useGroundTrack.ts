import { useEffect, useState } from 'react';

import { ApiError, fetchTrack, isAbortError } from '../api/issClient';
import type { Track } from '../types/iss';

export const TRACK_REFRESH_MS = 5 * 60 * 1_000;
const RETRY_AFTER_FAILURE_MS = 30_000;

export interface GroundTrackState {
  data: Track | null;
  error: string | null;
}

export function useGroundTrack(): GroundTrackState {
  const [data, setData] = useState<Track | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let inFlight: AbortController | null = null;

    const load = async (): Promise<void> => {
      inFlight = new AbortController();
      let succeeded = false;
      try {
        const track = await fetchTrack({}, inFlight.signal);
        if (cancelled) return;

        succeeded = true;
        setData(track);
        setError(null);
      } catch (caught) {
        if (cancelled || isAbortError(caught)) return;
        setError(caught instanceof ApiError ? caught.message : 'Could not load the ground track');
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(
            () => void load(),
            succeeded ? TRACK_REFRESH_MS : RETRY_AFTER_FAILURE_MS,
          );
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      inFlight?.abort();
    };
  }, []);

  return { data, error };
}
