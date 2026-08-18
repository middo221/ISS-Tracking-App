import { describe, expect, it } from 'vitest';

import { formatClock, formatElapsed, secondsBetween } from '../../src/utils/time';

describe('formatClock', () => {
  it('renders a UTC clock reading', () => {
    expect(formatClock('2026-08-17T04:12:09Z')).toBe('04:12:09 UTC');
  });

  it('does not shift with the local timezone', () => {
    expect(formatClock('2026-08-17T23:59:59Z')).toBe('23:59:59 UTC');
  });

  it('falls back for an unparseable timestamp', () => {
    expect(formatClock('not a date')).toBe('—');
  });
});

describe('formatElapsed', () => {
  it.each([
    [0, '0s'],
    [14, '14s'],
    [59, '59s'],
    [60, '1m 0s'],
    [134, '2m 14s'],
    [3_600, '1h 0m'],
    [7_845, '2h 10m'],
  ])('formats %s seconds as %s', (seconds, expected) => {
    expect(formatElapsed(seconds)).toBe(expected);
  });
});

describe('secondsBetween', () => {
  it('rounds to whole seconds', () => {
    expect(secondsBetween(1_000, 4_400)).toBe(3);
  });

  it('never reports a negative gap', () => {
    expect(secondsBetween(5_000, 1_000)).toBe(0);
  });
});
