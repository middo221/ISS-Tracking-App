import { useMemo } from 'react';
import { Polyline } from 'react-leaflet';

import type { Track } from '../types/iss';
import { futureTrackStyle, pastTrackStyle } from '../utils/mapStyles';
import { findBoundaryIndex, splitTrackAtBoundary, worldCopies } from '../utils/track';

interface GroundTrackProps {
  track: Track;
  nowMs: number;
}

export function GroundTrack({ track, nowMs }: GroundTrackProps): React.JSX.Element {
  const boundary = useMemo(() => findBoundaryIndex(track.points, nowMs), [track.points, nowMs]);

  // Keyed on the boundary rather than the clock, so the polylines are only rebuilt when a
  // point actually crosses from future to past.
  const { past, future } = useMemo(
    () => splitTrackAtBoundary(track.points, boundary),
    [track.points, boundary],
  );

  const pastCopies = useMemo(() => worldCopies(past), [past]);
  const futureCopies = useMemo(() => worldCopies(future), [future]);

  return (
    <>
      {pastCopies.map((line, index) => (
        <Polyline key={`past-${String(index)}`} positions={line} pathOptions={pastTrackStyle()} />
      ))}
      {futureCopies.map((line, index) => (
        <Polyline
          key={`future-${String(index)}`}
          positions={line}
          pathOptions={futureTrackStyle()}
        />
      ))}
    </>
  );
}
