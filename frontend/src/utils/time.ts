export function parseUtc(timestamp: string): number {
  return Date.parse(timestamp);
}

export function secondsBetween(fromMs: number, toMs: number): number {
  return Math.max(0, Math.round((toMs - fromMs) / 1000));
}

/** Clock reading in UTC, e.g. "04:12:09 UTC". */
export function formatClock(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '—';

  const pad = (value: number): string => String(value).padStart(2, '0');
  return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())} UTC`;
}

/** Short elapsed-time label for status copy, e.g. "14s" or "2m 14s". */
export function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;

  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
