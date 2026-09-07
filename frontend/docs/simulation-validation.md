# Earthquake Simulation setup — implementation and validation

Verified 2026-09-08 for TASK 14B-G (Scientific Ground-Motion Scenario Implementation). Scope is limited to `frontend/` and `/simulation` plus scenario contract client.

## Google Maps architecture (Person 2 boundary preserved)

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
- **Person 2 boundary**: Loader, APIProvider, and fallback error handling remain untouched.

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
