import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'

// Configure Vite-bundled MapLibre web worker once at module initialization
setWorkerUrl(workerUrl)

/**
 * Official verified OpenFreeMap dark vector tile style endpoint.
 * Requires no API key or credentials.
 */
export const OPENFREEMAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/dark'

/**
 * Default Turkey geographic boundaries and center for MapLibre.
 * Coordinates are [longitude, latitude] per GeoJSON / MapLibre standards.
 */
export const TURKEY_MAP_CENTER: { longitude: number; latitude: number } = {
  longitude: 35.0,
  latitude: 39.0,
}

export const TURKEY_MAP_INITIAL_ZOOM = 5

/**
 * Bounding box for Turkey [west, south, east, north]:
 * [[25.5, 35.5], [45.0, 42.5]]
 */
export const TURKEY_MAP_BOUNDS: [[number, number], [number, number]] = [
  [25.5, 35.5],
  [45.0, 42.5],
]

export const MAP_LOAD_TIMEOUT_MS = 20_000
