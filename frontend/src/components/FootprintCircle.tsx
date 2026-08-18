import { Circle } from 'react-leaflet';

import type { GeoPoint } from '../types/iss';
import { footprintStyle } from '../utils/mapStyles';

const METRES_PER_KILOMETRE = 1_000;

interface FootprintCircleProps {
  centre: GeoPoint;
  radiusKm: number;
}

export function FootprintCircle({ centre, radiusKm }: FootprintCircleProps): React.JSX.Element {
  return (
    <Circle
      center={[centre.latitude, centre.longitude]}
      radius={radiusKm * METRES_PER_KILOMETRE}
      pathOptions={footprintStyle()}
    />
  );
}
