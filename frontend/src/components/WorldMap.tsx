import { useEffect } from 'react';
import { MapContainer, TileLayer, useMap, ZoomControl } from 'react-leaflet';
import type { ReactNode } from 'react';

// `||` rather than `??`: an unset build arg arrives as an empty string, not undefined.
// The basemap is split in two so each half can be styled on its own: the base carries the
// land, water and country borders, while the labels ride above it on a transparent layer
// that can be sharpened without touching the basemap underneath.
const TILE_URL: string =
  import.meta.env.VITE_TILE_URL ||
  'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png';

// Voyager's label layer is drawn without a halo around the glyphs, unlike the dark one,
// and is designed to sit on the voyager basemap above.
const TILE_LABELS_URL: string =
  import.meta.env.VITE_TILE_LABELS_URL ||
  'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png';

const TILE_ATTRIBUTION: string =
  import.meta.env.VITE_TILE_ATTRIBUTION ||
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

const TILE_SIZE_PX = 256;

/** Keeps the smallest zoom at whatever still covers the viewport, so no dead space shows. */
function FillViewport(): null {
  const map = useMap();

  useEffect(() => {
    const apply = (): void => {
      const { x, y } = map.getSize();
      const fillingZoom = Math.max(1, Math.ceil(Math.log2(Math.max(x, y) / TILE_SIZE_PX)));

      map.setMinZoom(fillingZoom);
      if (map.getZoom() < fillingZoom) map.setZoom(fillingZoom);
    };

    apply();
    map.on('resize', apply);
    return () => {
      map.off('resize', apply);
    };
  }, [map]);

  return null;
}

interface WorldMapProps {
  children?: ReactNode;
}

export function WorldMap({ children }: WorldMapProps): React.JSX.Element {
  return (
    <MapContainer
      className="world-map"
      center={[15, 0]}
      zoom={3}
      minZoom={2}
      maxZoom={9}
      worldCopyJump
      zoomControl={false}
      attributionControl
      preferCanvas
    >
      {/* Explicit zIndex rather than relying on mount order for the label stacking. */}
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} zIndex={1} />
      <TileLayer url={TILE_LABELS_URL} className="world-map__labels" zIndex={2} />

      <ZoomControl position="topright" />
      <FillViewport />
      {children}
    </MapContainer>
  );
}
