import L from 'leaflet';
import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import type { Marker as LeafletMarker } from 'leaflet';

import type { GeoPoint } from '../types/iss';
import { bearingDegrees, interpolatePoint } from '../utils/coordinates';

const ICON_SIZE_PX = 36;
const STATIONARY_EPSILON_DEGREES = 1e-9;

// The glyph points up, so rotating it by the bearing aims it along the direction of travel.
const ICON_HTML = `
  <div class="iss-marker__rotor">
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path class="iss-marker__nose" d="M16 3.5l3.4 6h-6.8z" />
      <rect class="iss-marker__panel" x="3" y="12" width="9" height="8" rx="1.2" />
      <rect class="iss-marker__panel" x="20" y="12" width="9" height="8" rx="1.2" />
      <line class="iss-marker__boom" x1="12" y1="16" x2="20" y2="16" />
      <circle class="iss-marker__body" cx="16" cy="16" r="3.6" />
    </svg>
  </div>
`;

const issIcon = L.divIcon({
  className: 'iss-marker',
  html: ICON_HTML,
  iconSize: [ICON_SIZE_PX, ICON_SIZE_PX],
  iconAnchor: [ICON_SIZE_PX / 2, ICON_SIZE_PX / 2],
});

function applyHeading(marker: LeafletMarker, headingDegrees: number): void {
  marker.getElement()?.style.setProperty('--iss-heading', `${headingDegrees}deg`);
}

interface IssMarkerProps {
  target: GeoPoint;
  animate: boolean;
  durationMs: number;
}

/**
 * Driven imperatively rather than through props: the marker is repainted every frame to
 * glide between polls, and pushing 60 position updates a second through React would
 * re-render the whole map tree.
 */
export function IssMarker({ target, animate, durationMs }: IssMarkerProps): null {
  const map = useMap();
  const markerRef = useRef<LeafletMarker | null>(null);
  const renderedRef = useRef<GeoPoint>(target);
  const headingRef = useRef(0);
  const frameRef = useRef(0);

  useEffect(() => {
    const marker = L.marker([renderedRef.current.latitude, renderedRef.current.longitude], {
      icon: issIcon,
      interactive: false,
      keyboard: false,
      zIndexOffset: 1_000,
    });
    marker.addTo(map);
    markerRef.current = marker;
    applyHeading(marker, headingRef.current);

    return () => {
      window.cancelAnimationFrame(frameRef.current);
      marker.remove();
      markerRef.current = null;
    };
  }, [map]);

  useEffect(() => {
    const marker = markerRef.current;
    if (marker === null) return;

    const from = renderedRef.current;
    const moved =
      Math.abs(from.latitude - target.latitude) > STATIONARY_EPSILON_DEGREES ||
      Math.abs(from.longitude - target.longitude) > STATIONARY_EPSILON_DEGREES;

    if (moved) headingRef.current = bearingDegrees(from, target);
    applyHeading(marker, headingRef.current);

    if (!animate || !moved) {
      renderedRef.current = target;
      marker.setLatLng([target.latitude, target.longitude]);
      return;
    }

    const startedAt = performance.now();
    const step = (frameTime: number): void => {
      const fraction = Math.min(1, (frameTime - startedAt) / durationMs);
      const point = interpolatePoint(from, target, fraction);

      renderedRef.current = point;
      markerRef.current?.setLatLng([point.latitude, point.longitude]);

      if (fraction < 1) frameRef.current = window.requestAnimationFrame(step);
    };

    frameRef.current = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(frameRef.current);
  }, [target, animate, durationMs]);

  return null;
}
