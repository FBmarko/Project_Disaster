/** Development input settings, not scientific restrictions or probability estimates. */
export const SIMULATION_INPUTS = {
  magnitude: { min: 4, max: 8, step: 0.1, default: 6 },
  depthKm: { min: 1, max: 50, step: 1, default: 20, presets: [5, 10, 20, 30] },
  radiusKm: { options: [25, 50, 100, 150], default: 50 },
} as const

export const SIMULATION_MAP = {
  center: { lat: 39, lng: 35 },
  zoom: 5,
  // Fit Turkey on the first render, including narrow viewports. No location is preselected.
  bounds: { west: 25.5, south: 35.5, east: 45, north: 42.5, padding: 24 },
  loadTimeoutMs: 20_000,
} as const

/** Google's documented development map ID enables AdvancedMarker; it is not an API key. */
export const DEVELOPMENT_MAP_ID = 'DEMO_MAP_ID'

export const BACKEND_PENDING_MESSAGE =
  'Simülasyon servisi backend entegrasyonu tamamlandığında aktif olacaktır.'
