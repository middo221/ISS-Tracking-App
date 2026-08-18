import { useEffect, useState } from 'react';

/** Re-renders on a fixed cadence so elapsed-time readouts keep counting. */
export function useNow(intervalMs = 1_000): number {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);

  return nowMs;
}
