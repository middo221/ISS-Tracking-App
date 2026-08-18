/** Mirrors the payloads documented under /api/v1. Timestamps are UTC ISO-8601 with a `Z`. */

export interface Position {
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude_km: number;
  velocity_kmh: number;
  footprint_radius_km: number;
  tle_epoch: string;
}

export interface TrackPoint {
  timestamp: string;
  latitude: number;
  longitude: number;
}

export interface Track {
  generated_at: string;
  step_seconds: number;
  points: TrackPoint[];
}

export interface HealthStatus {
  status: string;
  tle_age_seconds: number;
}

export interface ApiErrorBody {
  detail: string;
  code: string;
}

export interface TrackQuery {
  minutesBehind?: number;
  minutesAhead?: number;
  stepSeconds?: number;
}

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

/** Leaflet's positional shape: [latitude, longitude]. */
export type LatLngTuple = [number, number];
