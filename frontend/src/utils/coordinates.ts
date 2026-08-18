import type { GeoPoint } from '../types/iss';

/** A jump larger than this between consecutive points means the path wrapped the globe. */
export const ANTIMERIDIAN_JUMP_DEGREES = 180;

const toRadians = (degrees: number): number => (degrees * Math.PI) / 180;
const toDegrees = (radians: number): number => (radians * 180) / Math.PI;

/** Wraps any longitude into [-180, 180). */
export function normalizeLongitude(longitude: number): number {
  return ((((longitude + 180) % 360) + 360) % 360) - 180;
}

/** Signed shortest angular distance from one longitude to another, in [-180, 180). */
export function longitudeDelta(from: number, to: number): number {
  return normalizeLongitude(to - from);
}

/**
 * Removes the ±360° snap-backs from a wrapped longitude series.
 *
 * Longitudes arrive clamped to [-180, 180], so a track running east past +180 reappears at
 * -180 and a polyline drawn through it doubles back across the entire map. Letting the
 * values run on instead (179, 180, 181...) keeps the path continuous: Leaflet projects
 * longitudes outside the nominal range straight onto the repeated world copies, so the line
 * crosses the dateline unbroken rather than being cut into segments there.
 */
export function unwrapLongitudes(longitudes: readonly number[]): number[] {
  let offset = 0;

  return longitudes.map((longitude, index) => {
    const previous = longitudes[index - 1];
    if (previous !== undefined) {
      const step = longitude - previous;
      if (step > ANTIMERIDIAN_JUMP_DEGREES) offset -= 360;
      else if (step < -ANTIMERIDIAN_JUMP_DEGREES) offset += 360;
    }
    return longitude + offset;
  });
}

/** Initial great-circle bearing from one point to another, in degrees clockwise from north. */
export function bearingDegrees(from: GeoPoint, to: GeoPoint): number {
  const fromLat = toRadians(from.latitude);
  const toLat = toRadians(to.latitude);
  const deltaLon = toRadians(longitudeDelta(from.longitude, to.longitude));

  const y = Math.sin(deltaLon) * Math.cos(toLat);
  const x =
    Math.cos(fromLat) * Math.sin(toLat) - Math.sin(fromLat) * Math.cos(toLat) * Math.cos(deltaLon);

  return (toDegrees(Math.atan2(y, x)) + 360) % 360;
}

/** Interpolates between two subpoints, taking the short way round at the antimeridian. */
export function interpolatePoint(from: GeoPoint, to: GeoPoint, fraction: number): GeoPoint {
  const clamped = Math.min(Math.max(fraction, 0), 1);
  return {
    latitude: from.latitude + (to.latitude - from.latitude) * clamped,
    longitude: normalizeLongitude(
      from.longitude + longitudeDelta(from.longitude, to.longitude) * clamped,
    ),
  };
}

function formatDegrees(value: number, positive: string, negative: string): string {
  const hemisphere = value >= 0 ? positive : negative;
  return `${Math.abs(value).toFixed(4)}° ${hemisphere}`;
}

export function formatLatitude(latitude: number): string {
  return formatDegrees(latitude, 'N', 'S');
}

export function formatLongitude(longitude: number): string {
  return formatDegrees(normalizeLongitude(longitude), 'E', 'W');
}

export function formatAltitude(kilometres: number): string {
  return `${kilometres.toFixed(1)} km`;
}

export function formatSpeed(kilometresPerHour: number): string {
  return `${Math.round(kilometresPerHour).toLocaleString('en-GB')} km/h`;
}
