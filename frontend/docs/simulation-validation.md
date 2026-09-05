# Earthquake Simulation setup — implementation and validation

Verified 2026-09-03. Scope is limited to `frontend/` and `/simulation`.

## Google Maps architecture

- Package: `@vis.gl/react-google-maps` 1.9.0 (single wrapper library).
- `SimulationMap` reads only `import.meta.env.VITE_GOOGLE_MAPS_API_KEY`. A blank
  or missing value renders “Google Maps API anahtarı yapılandırılmamış.” and
  does not mount `APIProvider` or load the Google wrapper chunk.
- The optional `VITE_GOOGLE_MAPS_MAP_ID` enables a production cloud map ID;
  otherwise Google's documented `DEMO_MAP_ID` is used for development. A map
  ID is required by `AdvancedMarker` and is not an API key.
- `GoogleSimulationMap` uses `APIProvider`, a roadmap `Map`, `AdvancedMarker`
  and `Pin`. It sets Turkish language/region, requests no optional Places,
  Geocoding, Directions or other libraries, and disables attribution telemetry
  specific to the wrapper. It does not use browser geolocation.
- Initial center is latitude 39, longitude 35, fallback zoom 5. The actual first
  view fits bounds west 25.5, south 35.5, east 45, north 42.5 so Turkey remains
  visible at desktop and narrow widths.
- A map click consumes the wrapper's numeric `event.detail.latLng`, replaces the
  one stored coordinate pair and renders exactly zero or one marker. No reverse
  geocoding occurs. “Konumu Temizle” removes both coordinates and marker.
- The API loader's error callback, Google's documented `gm_authFailure`, a
  20-second no-tiles timeout and a React error boundary all lead to the visible
  “Google Maps yüklenemedi.” state with a reload action. Loader errors are not
  logged by application code because external error URLs can contain the key.
- The Google wrapper is lazy-loaded and isolated from other routes.

The effective development environment had **no configured Google Maps API key**.
No key value was read, printed, captured or committed. Consequently, live Google
base-map rendering, live map clicking, marker placement/movement and provider
error callbacks could not be exercised. Their production integration was checked
by TypeScript/build and source inspection. The missing-key path was verified and
the page contained no `maps.googleapis.com` script.

## Simulation draft and UI

- `SimulationDraft` holds nullable latitude/longitude and numeric magnitude,
  depth and radius. `SimulationRequestDraft` represents a future payload shape;
  it is not an API contract and is never transported or persisted.
- The reducer owns location selection/replacement/clearing, settings changes and
  the local submit status. Every edit clears stale availability feedback.
- Pure validation requires finite geographic coordinates, 4.0–8.0 Mw magnitude,
  1–50 km depth and one of 25/50/100/150 km radii. The current UI supplies
  5/10/20/30 km depth presets.
- Full numeric coordinate precision remains in state/payload. `toFixed(4)` is
  confined to `LocationSummary` display text.
- Before selection, all controls and “Senaryoyu Hazırla” are disabled and an
  instruction is visible. A valid action prepares and validates the local payload,
  then explains that results are unavailable. It performs no navigation, timeout
  simulation, backend request, calculation or storage.
- Semantic regions, headings, fieldsets, labels, native inputs/buttons, output,
  `aria-live`, `aria-invalid`, focus styles and non-color disabled/feedback text
  provide the accessibility structure. The map region includes an instruction.

## Verification

| Check | Result |
| --- | --- |
| `npm run validate:simulation` | PASS — 11 validation/reducer scenarios |
| `npm run validate:provinces` | PASS — 81/81 provinces |
| `npm run validate:faults` | PASS — 321 real fault features |
| `npm run build` | PASS — TypeScript + Vite production build |
| `npm run lint` | PASS — oxlint |

The offline simulation validator tests initial invalid state, exact precision,
coordinate bounds/non-finite/type rejection, control boundaries, radius options,
valid local submit, location replacement, clearing, settings changes
and malformed map coordinates. It imports the same constants, types, reducer and
validation helpers as the application and performs no network call.

Local Chromium verification covered:

- `/simulation` loads and reports the missing API-key state without a Google script.
- Map and settings cards are side by side at 1440 px and stack at 768/390/320 px.
  No page-level horizontal overflow occurred at those widths.
- Settings component integration using an isolated local harness: exact test
  coordinates enabled controls; slider changed to 7.9 Mw; 30 km depth and
  150 km radius selected; the primary action displayed only the unavailable-results
  message and stayed on the same URL; Clear removed coordinates, disabled it and cleared
  stale feedback. The harness did not mount a map or provider.
- Missing-key and map-error presentation states are readable. Sidebar marks
  Deprem Simülasyonu as current. No console warning/error was recorded in tested
  missing-key/component flows.
- Existing HomePage and FaultLinesPage behavior is unchanged; their source files
  were not modified and existing validators still pass.

Physical touch hardware and a separate screen-reader application were not used.
The integration harness was ignored local QA content and removed after testing.

## File inventory

Created:

- `scripts/validate-simulation.ts`
- `src/types/simulation.ts`
- `src/constants/simulation.ts`
- `src/utils/simulationDraft.ts`
- `src/components/simulation/SimulationMap.tsx`
- `src/components/simulation/GoogleSimulationMap.tsx`
- `src/components/simulation/SimulationMapState.tsx`
- `src/components/simulation/SimulationMapBoundary.tsx`
- `src/components/simulation/SimulationSettingsPanel.tsx`
- `src/components/simulation/LocationSummary.tsx`
- `src/components/simulation/MagnitudeControl.tsx`
- `src/components/simulation/DepthControl.tsx`
- `src/components/simulation/ImpactRadiusControl.tsx`
- `docs/simulation-validation.md`

Modified:

- `.env.example`
- `README.md`
- `package.json`
- `package-lock.json`
- `src/pages/SimulationPage.tsx`
- `src/vite-env.d.ts`

All paths are relative to `frontend/`. No backend or existing completed-page file
was modified.
