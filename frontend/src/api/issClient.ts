import type { ApiErrorBody, HealthStatus, Position, Track, TrackQuery } from '../types/iss';

// `||` rather than `??`: an unset build arg arrives as an empty string, not undefined.
const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const body = value as Record<string, unknown>;
  return typeof body.detail === 'string' && typeof body.code === 'string';
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      signal: signal ?? null,
      headers: { Accept: 'application/json' },
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause;
    throw new ApiError('Could not reach the tracking service', 'network_error', 0);
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = isApiErrorBody(body) ? body.detail : `Request failed (${response.status})`;
    const code = isApiErrorBody(body) ? body.code : 'http_error';
    throw new ApiError(detail, code, response.status);
  }

  return (await response.json()) as T;
}

export function fetchPosition(signal?: AbortSignal): Promise<Position> {
  return getJson<Position>('/iss/position', signal);
}

export function fetchTrack(query: TrackQuery = {}, signal?: AbortSignal): Promise<Track> {
  const params = new URLSearchParams();
  if (query.minutesBehind !== undefined) params.set('minutes_behind', String(query.minutesBehind));
  if (query.minutesAhead !== undefined) params.set('minutes_ahead', String(query.minutesAhead));
  if (query.stepSeconds !== undefined) params.set('step_seconds', String(query.stepSeconds));

  const suffix = params.size > 0 ? `?${params.toString()}` : '';
  return getJson<Track>(`/iss/track${suffix}`, signal);
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  return getJson<HealthStatus>('/health', signal);
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}
