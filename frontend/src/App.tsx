import { useMemo } from 'react';

import { FootprintCircle } from './components/FootprintCircle';
import { GroundTrack } from './components/GroundTrack';
import { IssMarker } from './components/IssMarker';
import { TelemetryPanel } from './components/TelemetryPanel';
import { WorldMap } from './components/WorldMap';
import { useGroundTrack } from './hooks/useGroundTrack';
import { useIssPosition } from './hooks/useIssPosition';
import { useNow } from './hooks/useNow';
import { usePrefersReducedMotion } from './hooks/usePrefersReducedMotion';
import type { GeoPoint } from './types/iss';

export default function App(): React.JSX.Element {
  const position = useIssPosition();
  const track = useGroundTrack();
  const prefersReducedMotion = usePrefersReducedMotion();
  const nowMs = useNow();

  // Kept stable between polls so the marker animation is not restarted every second.
  const subpoint = useMemo<GeoPoint | null>(
    () =>
      position.data === null
        ? null
        : { latitude: position.data.latitude, longitude: position.data.longitude },
    [position.data],
  );

  return (
    <div className="app">
      <TelemetryPanel
        position={position.data}
        error={position.error}
        trackError={track.error}
        isStale={position.isStale}
        secondsSinceContact={position.secondsSinceContact}
        pollIntervalMs={position.pollIntervalMs}
      />

      <div className="app__map">
        <WorldMap>
          {track.data !== null && <GroundTrack track={track.data} nowMs={nowMs} />}
          {position.data !== null && subpoint !== null && (
            <>
              <FootprintCircle centre={subpoint} radiusKm={position.data.footprint_radius_km} />
              <IssMarker
                target={subpoint}
                animate={!prefersReducedMotion}
                durationMs={position.pollIntervalMs}
              />
            </>
          )}
        </WorldMap>
      </div>
    </div>
  );
}
