# Earthquake Simulation setup — implementation and validation

Verified 2026-09-08 for TASK 14B-G (Scientific Ground-Motion Scenario Implementation). Scope is limited to `frontend/` and `/simulation` plus scenario contract client.

## Map visualization architecture (MapLibre GL JS + OpenFreeMap)

- Packages: `maplibre-gl` 6.8.x and `react-map-gl` 8.1.x.
- MapLibre web worker is initialized using Vite's worker bundler import in `src/config/map.ts`.
- Basemap: Public vector tiles from OpenFreeMap (`https://tiles.openfreemap.org/styles/dark`), requiring zero API keys or external credentials.
- `MapLibreSimulationMap` provides interactive map rendering, Turkey view fitting, and click-to-select point positioning.
- Coordinates follow GeoJSON / MapLibre standard `[longitude, latitude]`.
- Click on the map records `latitude: event.lngLat.lat, longitude: event.lngLat.lng`.
- Initial bounds: west 25.5, south 35.5, east 45, north 42.5.
- Attribution is preserved visibly on the map (OpenStreetMap, OpenFreeMap).
- Controlled fallback UI is displayed if network access to OpenFreeMap fails or times out.
- Map component is code-split and lazy-loaded.


## Scientific scenario simulation model & UI (TASK 14B-G)

- Ground-Motion Model: Akkar, Sandıkkaya & Bommer (2014) point-source model (`AkkarEtAlRhyp2014`).
- Published DOI: 10.1007/s10518-013-9461-4.
- Endpoint: `POST /api/v1/earthquake-hazards/scenario`.
- Parameters:
  - Epicenter: Geographic latitude [-90, 90] and longitude [-180, 180].
  - Moment magnitude ($M_w$): 4.0–7.6 Mw (AFET360 calibration guard, step 0.1).
  - Focal depth: Backend/model product guard is depth > 0 and <= 30 km; frontend client input sanity bound is 0.1 km (presets: 5, 10, 20, 30 km; 0.1 km is not a published Akkar scientific lower limit).
  - Fault mechanism: Mandatory selection of `strike_slip` ($0^\circ$), `normal` ($-90^\circ$), or `reverse` ($+90^\circ$). No silent default.
  - Calculation radius: 25, 50, 100, 150 km (labeled as *Hesaplama Yarıçapı*, not damage/impact radius).
  - Site condition: Reference rock assumption ($V_{s30} = 800\text{ m/s}$).
- UI Components:
  - `SimulationSettingsPanel`: Coordinates scenario parameter input, validation, calculation submission, and result presentation.
  - `MechanismControl`: Accessible radio group for fault mechanism selection with descriptions.
  - `ImpactRadiusControl`: Scientific radius selector for radial attenuation profiling.
  - `ScenarioResultView`: Renders epicentral median PGA estimate, $\pm 1\sigma$ range ($\sigma_{\ln} \approx 0.7347$), 5-km radial attenuation table, model citation, and prominent scientific disclaimer.
- Scientific Boundaries Enforced:
  - Answers strictly: "If a user-defined earthquake with these parameters occurred, what median PGA would the selected Akkar et al. (2014) GMPE estimate as a function of distance?"
  - Not an earthquake prediction or forecast.
  - Not a building damage, vulnerability, or casualty estimate.
  - Not combined, blended, or scaled with GSHM v2026.1 hazard data.
  - No mock or fake results; uses live pure-Python mathematical evaluation.

## Verification

| Check | Result |
| --- | --- |
| `npm run validate:api` | PASS — Faults, earthquakes, OSM, hazard, and scenario response contracts |
| `npm run validate:simulation` | PASS — 13 validation/reducer/parameter scenarios |
| `npm run validate:provinces` | PASS — 81/81 provinces |
| `npm run validate:faults` | PASS — 321 real fault features |
| `npm run validate:assembly` | PASS — Assembly area contracts |
| `npm run validate:preparedness` | PASS — Preparedness guide contracts |
| `npm run validate:theme` | PASS — Theme tokens |
| `npm run build` | PASS — TypeScript + Vite production build |
| `npm run lint` | PASS — oxlint |

The offline simulation validator tests initial invalid state, mandatory mechanism requirement, exact coordinate precision,
coordinate bounds/non-finite/type rejection, magnitude bounds (4.0–7.6), radius options,
valid local submit / loading lifecycle, location replacement, clearing, settings changes,
and error handling.
