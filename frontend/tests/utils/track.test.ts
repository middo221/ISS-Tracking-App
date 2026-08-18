import { describe, expect, it } from 'vitest';

import type { TrackPoint } from '../../src/types/iss';
import {
  WORLD_COPY_OFFSETS,
  findBoundaryIndex,
  splitTrackAtBoundary,
  splitTrackByTime,
  unwrapTrack,
  worldCopies,
} from '../../src/utils/track';

const START_MS = Date.parse('2026-08-17T04:00:00Z');
const STEP_SECONDS = 30;
const ANTIMERIDIAN_JUMP_DEGREES = 180;

function buildTrack(longitudes: readonly number[]): TrackPoint[] {
  return longitudes.map((longitude, index) => ({
    timestamp: new Date(START_MS + index * STEP_SECONDS * 1000).toISOString(),
    latitude: 0,
    longitude,
  }));
}

function largestStep(line: readonly [number, number][]): number {
  return line.reduce((largest, current, index) => {
    const previous = line[index - 1];
    if (previous === undefined) return largest;
    return Math.max(largest, Math.abs(current[1] - previous[1]));
  }, 0);
}

describe('findBoundaryIndex', () => {
  it('points at the first future sample', () => {
    expect(findBoundaryIndex(buildTrack([0, 10, 20, 30]), START_MS + 45_000)).toBe(2);
  });

  it('returns 0 when the whole track is still ahead', () => {
    expect(findBoundaryIndex(buildTrack([0, 10]), START_MS - 60_000)).toBe(0);
  });

  it('returns the length when the whole track is behind', () => {
    const track = buildTrack([0, 10]);

    expect(findBoundaryIndex(track, START_MS + 600_000)).toBe(track.length);
  });
});

describe('unwrapTrack', () => {
  it('produces one unbroken line across the dateline', () => {
    const line = unwrapTrack(buildTrack([170, 179, -179, -170]));

    expect(line.map(([, longitude]) => longitude)).toEqual([170, 179, 181, 190]);
    expect(largestStep(line)).toBeLessThanOrEqual(ANTIMERIDIAN_JUMP_DEGREES);
  });

  it('keeps latitudes alongside their longitudes', () => {
    const track = buildTrack([170, -179]);
    track[0]!.latitude = 45;
    track[1]!.latitude = -45;

    expect(unwrapTrack(track)).toEqual([
      [45, 170],
      [-45, 181],
    ]);
  });
});

describe('splitTrackAtBoundary', () => {
  it('shares a point between past and future so the line stays joined', () => {
    const { past, future } = splitTrackByTime(buildTrack([0, 10, 20, 30]), START_MS + 45_000);

    expect(past.at(-1)).toEqual([0, 10]);
    expect(future[0]).toEqual([0, 10]);
  });

  it('keeps both halves on one continuous longitude scale across the dateline', () => {
    const { past, future } = splitTrackByTime(
      buildTrack([170, 179, -179, -170]),
      START_MS + 75_000,
    );

    // The join must not jump a world: whatever the value, both halves meet on it.
    expect(past.at(-1)).toEqual(future[0]);
    expect(largestStep(past)).toBeLessThanOrEqual(ANTIMERIDIAN_JUMP_DEGREES);
    expect(largestStep(future)).toBeLessThanOrEqual(ANTIMERIDIAN_JUMP_DEGREES);
  });

  it('puts everything in the future before the track starts', () => {
    const { past, future } = splitTrackByTime(buildTrack([0, 10, 20]), START_MS - 1_000);

    expect(past).toEqual([]);
    expect(future).toHaveLength(3);
  });

  it('clamps a boundary beyond the ends of the track', () => {
    const track = buildTrack([0, 10, 20]);

    expect(splitTrackAtBoundary(track, 99).past).toHaveLength(3);
    expect(splitTrackAtBoundary(track, -5).past).toEqual([]);
  });
});

describe('worldCopies', () => {
  it('repeats the line once per world offset', () => {
    const copies = worldCopies([
      [0, 10],
      [0, 20],
    ]);

    expect(copies).toHaveLength(WORLD_COPY_OFFSETS.length);
    expect(copies.map((line) => line[0]?.[1])).toEqual(WORLD_COPY_OFFSETS.map((o) => 10 + o));
  });

  it('draws nothing for a line too short to render', () => {
    expect(worldCopies([])).toEqual([]);
    expect(worldCopies([[0, 10]])).toEqual([]);
  });
});
