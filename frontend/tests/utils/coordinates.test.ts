import { describe, expect, it } from 'vitest';

import {
  ANTIMERIDIAN_JUMP_DEGREES,
  bearingDegrees,
  formatAltitude,
  formatLatitude,
  formatLongitude,
  formatSpeed,
  interpolatePoint,
  longitudeDelta,
  normalizeLongitude,
  unwrapLongitudes,
} from '../../src/utils/coordinates';

const point = (longitude: number, latitude = 0): { latitude: number; longitude: number } => ({
  latitude,
  longitude,
});

function largestStep(longitudes: readonly number[]): number {
  return longitudes.reduce((largest, current, index) => {
    const previous = longitudes[index - 1];
    if (previous === undefined) return largest;
    return Math.max(largest, Math.abs(current - previous));
  }, 0);
}

describe('unwrapLongitudes', () => {
  it('leaves a track that never crosses the dateline untouched', () => {
    expect(unwrapLongitudes([-20, 0, 20, 40])).toEqual([-20, 0, 20, 40]);
  });

  it('carries an eastbound track past +180 instead of snapping back', () => {
    expect(unwrapLongitudes([170, 179, -179, -170])).toEqual([170, 179, 181, 190]);
  });

  it('carries a westbound track past -180', () => {
    expect(unwrapLongitudes([-170, -179, 179, 170])).toEqual([-170, -179, -181, -190]);
  });

  it('never leaves a step wider than 180°, which is what would draw across the map', () => {
    const eastbound = Array.from({ length: 200 }, (_, index) =>
      normalizeLongitude(-170 + index * 3),
    );

    const unwrapped = unwrapLongitudes(eastbound);

    expect(largestStep(unwrapped)).toBeLessThanOrEqual(ANTIMERIDIAN_JUMP_DEGREES);
    expect(largestStep(eastbound)).toBeGreaterThan(ANTIMERIDIAN_JUMP_DEGREES);
  });

  it('keeps accumulating over several crossings', () => {
    expect(unwrapLongitudes([0, 170, -20, 150, -40])).toEqual([0, 170, 340, 510, 680]);
  });

  it('stays equivalent to the original once wrapped back', () => {
    const original = [100, 179, -179, -100, 20];

    for (const [index, unwrapped] of unwrapLongitudes(original).entries()) {
      expect(normalizeLongitude(unwrapped)).toBeCloseTo(
        normalizeLongitude(original[index] ?? 0),
        9,
      );
    }
  });

  it('handles empty and single-point input', () => {
    expect(unwrapLongitudes([])).toEqual([]);
    expect(unwrapLongitudes([42])).toEqual([42]);
  });

  it('does not react to latitude changes', () => {
    expect(unwrapLongitudes([point(10, -80).longitude, point(10, 80).longitude])).toEqual([10, 10]);
  });
});

describe('normalizeLongitude', () => {
  it.each([
    [0, 0],
    [180, -180],
    [-180, -180],
    [190, -170],
    [-190, 170],
    [540, -180],
  ])('maps %s to %s', (input, expected) => {
    expect(normalizeLongitude(input)).toBeCloseTo(expected, 9);
  });
});

describe('longitudeDelta', () => {
  it('takes the short way across the dateline', () => {
    expect(longitudeDelta(179, -179)).toBeCloseTo(2, 9);
    expect(longitudeDelta(-179, 179)).toBeCloseTo(-2, 9);
  });

  it('is a plain difference away from the dateline', () => {
    expect(longitudeDelta(10, 40)).toBeCloseTo(30, 9);
  });
});

describe('interpolatePoint', () => {
  it('returns the endpoints at the extremes', () => {
    const from = point(10, 0);
    const to = point(20, 10);

    expect(interpolatePoint(from, to, 0)).toEqual(from);
    expect(interpolatePoint(from, to, 1).longitude).toBeCloseTo(20, 9);
  });

  it('crosses the dateline the short way instead of sweeping the map', () => {
    const midpoint = interpolatePoint(point(179), point(-179), 0.5);

    expect(midpoint.longitude).toBeCloseTo(-180, 9);
  });

  it('clamps a fraction outside 0..1', () => {
    expect(interpolatePoint(point(0), point(10), 5).longitude).toBeCloseTo(10, 9);
    expect(interpolatePoint(point(0), point(10), -5).longitude).toBeCloseTo(0, 9);
  });
});

describe('bearingDegrees', () => {
  it('reads due east as 90°', () => {
    expect(bearingDegrees(point(0, 0), point(10, 0))).toBeCloseTo(90, 6);
  });

  it('reads due north as 0°', () => {
    expect(bearingDegrees(point(0, 0), point(0, 10))).toBeCloseTo(0, 6);
  });

  it('stays eastward across the dateline', () => {
    expect(bearingDegrees(point(179, 0), point(-179, 0))).toBeCloseTo(90, 6);
  });
});

describe('formatting', () => {
  it('labels hemispheres', () => {
    expect(formatLatitude(-12.4483)).toBe('12.4483° S');
    expect(formatLatitude(12.4483)).toBe('12.4483° N');
    expect(formatLongitude(145.9021)).toBe('145.9021° E');
    expect(formatLongitude(-145.9021)).toBe('145.9021° W');
  });

  it('formats altitude and speed with their units', () => {
    expect(formatAltitude(421.6789)).toBe('421.7 km');
    expect(formatSpeed(27584.3)).toBe('27,584 km/h');
  });
});
