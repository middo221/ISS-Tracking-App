import type { PathOptions } from 'leaflet';

/**
 * Path colours live in tokens.css so the palette has one home. Leaflet needs them as
 * JavaScript values, so they are read back off the document; the fallbacks keep the map
 * legible before stylesheets load and under jsdom in tests.
 */
const FALLBACKS: Record<string, string> = {
  '--color-map-live': '#0b7a5e',
  '--color-map-future': '#cf6412',
  '--color-map-past': '#4a5568',
};

export function cssToken(name: string): string {
  const fallback = FALLBACKS[name] ?? '';
  if (typeof document === 'undefined') return fallback;

  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value === '' ? fallback : value;
}

export function pastTrackStyle(): PathOptions {
  return {
    color: cssToken('--color-map-past'),
    weight: 2.5,
    opacity: 0.95,
    lineCap: 'round',
    lineJoin: 'round',
    interactive: false,
  };
}

export function futureTrackStyle(): PathOptions {
  return {
    color: cssToken('--color-map-future'),
    weight: 3,
    opacity: 0.95,
    // Short dashes with round caps read as an evenly spaced dotted line rather than a
    // chopped-up solid one, which suits a predicted path.
    dashArray: '2 7',
    lineCap: 'round',
    lineJoin: 'round',
    interactive: false,
  };
}

export function footprintStyle(): PathOptions {
  return {
    color: cssToken('--color-map-live'),
    weight: 1.5,
    opacity: 0.7,
    fillColor: cssToken('--color-map-live'),
    fillOpacity: 0.1,
    interactive: false,
  };
}
