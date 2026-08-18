/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base path of the API. Defaults to a same-origin `/api/v1`, which nginx proxies. */
  readonly VITE_API_BASE_URL?: string;
  /** Base tiles: land, water and country borders, without place names. */
  readonly VITE_TILE_URL?: string;
  /** Transparent overlay carrying only the place names. */
  readonly VITE_TILE_LABELS_URL?: string;
  readonly VITE_TILE_ATTRIBUTION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
