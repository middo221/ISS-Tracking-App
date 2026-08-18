import type { LatLngTuple, TrackPoint } from '../types/iss';
import { unwrapLongitudes } from './coordinates';

/**
 * The unwrapped track is drawn once per world copy either side of the primary one, so it
 * stays visible however far the viewer has panned around the globe.
 */
export const WORLD_COPY_OFFSETS = [-360, 0, 360];

export interface TrackSegments {
  past: LatLngTuple[];
  future: LatLngTuple[];
}

/** Index of the first point that has not happened yet, or the length if all are past. */
export function findBoundaryIndex(points: readonly TrackPoint[], nowMs: number): number {
  const index = points.findIndex((point) => Date.parse(point.timestamp) >= nowMs);
  return index === -1 ? points.length : index;
}

/** Track as one continuous line, with the antimeridian snap-backs unwrapped away. */
export function unwrapTrack(points: readonly TrackPoint[]): LatLngTuple[] {
  const longitudes = unwrapLongitudes(points.map((point) => point.longitude));

  return points.map((point, index): LatLngTuple => [
    point.latitude,
    longitudes[index] ?? point.longitude,
  ]);
}

/**
 * Splits the track into the part already flown and the part still to come. Unwrapping runs
 * over the whole track before slicing, so the two halves stay on the same continuous
 * longitude scale and meet rather than jumping a world apart.
 */
export function splitTrackAtBoundary(
  points: readonly TrackPoint[],
  boundaryIndex: number,
): TrackSegments {
  const line = unwrapTrack(points);
  const boundary = Math.min(Math.max(boundaryIndex, 0), line.length);

  return {
    past: line.slice(0, boundary),
    // Starts on the last past point so the two lines join instead of leaving a gap.
    future: line.slice(Math.max(0, boundary - 1)),
  };
}

export function splitTrackByTime(points: readonly TrackPoint[], nowMs: number): TrackSegments {
  return splitTrackAtBoundary(points, findBoundaryIndex(points, nowMs));
}

/** One copy of the line per world offset; nothing at all if there is no line to draw. */
export function worldCopies(line: readonly LatLngTuple[]): LatLngTuple[][] {
  if (line.length < 2) return [];

  return WORLD_COPY_OFFSETS.map((offset) =>
    line.map(([latitude, longitude]): LatLngTuple => [latitude, longitude + offset]),
  );
}
