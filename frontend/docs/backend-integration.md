# Backend integration audit — Step 9

Audited on 2026-09-04 against repository commit `fffff51` on
`feature/afet360-frontend`, before changing frontend source.

## API audit

The backend is a FastAPI foundation with one application endpoint: the health
check. **BACKEND ENDPOINT NOT AVAILABLE** for every requested product feature.
No product API integration can be implemented against the current contracts.

| Feature | Backend endpoint | Status | Frontend integration |
| --- | --- | --- | --- |
| Home province earthquake risk/hazard | None | NOT AVAILABLE | Existing development province data retained unchanged |
| Fault metadata, names and affected cities | None | NOT AVAILABLE | Local GEM geometry and existing detail states retained |
| Historical earthquakes related to faults | None (no general history endpoint either) | NOT AVAILABLE | No events or fault associations fabricated |
| Earthquake simulation | None | NOT AVAILABLE | Existing local form validation and unavailable state retained |
| Preparedness Guide / AI | None | NOT AVAILABLE | Existing profile form, no guide, permanent safety notice retained |
| Assembly Areas | None | NOT AVAILABLE | Existing empty `AssemblyArea[]` and search UI retained |
| Service health (outside product feature scope) | `GET /api/v1/health` with default configuration | AVAILABLE | Audited only; supplies no product data |

There are no partially available product contracts. For all six requested
capabilities, HTTP method, route, request/query schema, response schema and error
contract are **not defined**. UI types must not be treated as backend DTOs.

## Evidence and actual contract

Implementation was read, not inferred from filenames:

- `backend/app/main.py` constructs FastAPI and includes `api_router`.
- `backend/app/api/router.py` mounts `v1_router` under `settings.API_V1_PREFIX`.
- `backend/app/api/v1/router.py` includes only `health.router`.
- `backend/app/api/v1/endpoints/health.py` defines only `GET /health` and
  `HealthResponse`. It returns settings-derived service/version metadata.
- `backend/app/core/config.py` defaults `API_V1_PREFIX` to `/api/v1`,
  `APP_NAME` to `AFET360 API`, and `APP_VERSION` to `0.1.0`.
- `backend/tests/test_health.py` checks this default health response.
- `backend/README.md`, `backend/pyproject.toml`, and the safe backend environment
  template confirm foundation scope. Repository searches found no other
  controllers, registered routes, request/response models or product API specs.

### Health

- Method/path: `GET /api/v1/health` by default; prefix is configurable in backend.
- Request body: none. Query parameters: none. Authentication: none implemented.
- Success: HTTP 200, JSON with required string fields `status`, `service`,
  `version`. Default response:

  ```json
  { "status": "ok", "service": "AFET360 API", "version": "0.1.0" }
  ```

- Errors: no endpoint-specific error model, explicit error branch, or custom
  exception handler. No product error contract should be inferred from health.
- FastAPI documentation routes: `GET /docs`, `GET /redoc`, and
  `GET /openapi.json`. These are documentation, not product data APIs.
- No CORS middleware or frontend development proxy is configured in the checked
  source. Browser cross-origin integration will need an approved deployment or
  backend configuration when real product endpoints become available.

## Frontend behavior retained

- **Home:** `useProvinceRisk` still returns `mockProvinceRisk`, explicitly
  development UI data, not scientifically validated risk or hazard. No request
  runs and this is not a fallback after an API error. All 81 province geometries,
  tooltip/hover behavior and legend remain unchanged.
- **Fault Lines:** local GEM/EMME geometry remains authoritative for this UI.
  Names, cities and historical earthquake relationships are not supplied by the
  backend. Existing missing-data states remain; no spatially guessed earthquake
  associations are introduced.
- **Simulation:** latitude, longitude, magnitude, depth and radius remain local
  form inputs, not an invented request contract. Start validates the draft and
  shows the existing unavailable state. There is no backend status/result to
  display, polling or preparedness CTA. The page remains `/simulation`.
- **Preparedness:** city, disaster type, household size, children, elderly-person
  and pet choices remain a local profile. Results receive `null`; no AI provider
  is called. The desired `priorities`, `emergencyKit`, `communicationPlan` and
  `specialNeeds` string arrays are UI types, not an available backend response.
  When an endpoint exists, validate its output at runtime before rendering and
  reject malformed data. The existing notice remains unchanged:

  > Bu rehber genel hazırlık ve farkındalık amacıyla sunulmaktadır. Afet ve acil durumlarda AFAD ve ilgili resmî kurumların açıklama ve talimatlarını takip edin.

- **Assembly Areas:** no backend search mode exists. The local region and
  current-location flows do not send backend requests. `ASSEMBLY_AREAS` remains
  empty; no area cards, area markers or directions are invented. Existing
  selection/list/map wiring is retained for future verified records. Explicit
  current-location action and page-memory-only coordinate handling are unchanged.

No unused HTTP client, API modules, DTOs, artificial loading states or mapping
tests were added. Add the shared `VITE_API_BASE_URL` client, typed contract
mappers, Turkish loading/error/empty states, cancellation and duplicate-submit
guards when actual product endpoints can be connected. Never silently substitute
mock data for a failed real request.

## Cancelled results page

Removed the unused `/simulation-results` route, its route constant and placeholder
`SimulationResultsPage.tsx`. A reference search found only the route registration
and historical documentation; SimulationPage and validation scripts do not depend
on it. Unknown URLs use the existing redirect to Home. No replacement results
route or page was created. The sidebar remains Ana Sayfa, Fay Hatları, Deprem
Simülasyonu, Hazırlık Rehberi, Toplanma Alanları, divider, Hakkında.

## Environment

No environment files changed and no credentials were added.

| Variable | Current use |
| --- | --- |
| `VITE_API_BASE_URL` | Existing blank template; reserved for future project-backend requests, currently unused |
| `VITE_GOOGLE_MAPS_API_KEY` | Existing Google Maps environment key for Simulation and Assembly Areas; absent key retains configuration state |
| `VITE_GOOGLE_MAPS_MAP_ID` | Existing optional AdvancedMarker map ID |

Keep real values out of Git. No AI credential or direct provider SDK belongs in
the frontend. AboutPage content and all geographic assets are unchanged.

## Verification

All existing validation commands passed from `frontend/`:

- `npm run validate:provinces`: 81 canonical provinces and projection verified.
- `npm run validate:faults`: 321 real source features and geometry integrity.
- `npm run validate:simulation`: 11 checks passed.
- `npm run validate:preparedness`: 8 checks passed.
- `npm run validate:assembly`: 8 checks passed.
- `npm run build`: TypeScript and Vite passed; Vite reported a non-blocking
  warning for a main bundle over 500 kB.
- `npm run lint`: passed.

Headless Microsoft Edge via Playwright, against the local Vite server:

- All six product routes loaded at widths 1440, 768, 390 and 320 (24 checks),
  with no document horizontal overflow or browser console/page errors.
- Both `/simulation-results` and `/simulation/result/test` redirect to Home.
- Sidebar contains exactly the six expected links in order. Keyboard Enter
  opens it and Escape closes it.
- Fault keyboard selection works with Enter and Space; a second selection
  replaces the first.
- Preparedness invalid submission focuses the city field. Keyboard radio
  choices and repeated valid local submissions retain the no-guide status;
  editing clears that status. Safety notice remains present.
- Assembly invalid submission focuses the province field. Repeated region
  searches retain the honest unavailable-data state and create no directions.
- Simulation and Assembly Areas show their missing-Google-key states. Simulation
  start is disabled without a selected location.
- These browser flows made no external requests and left localStorage,
  sessionStorage and cookies empty. No real geolocation permission was requested.

Limitations: no real Google Maps key was configured, so live map clicks,
markers and directions were not exercised. No product endpoint exists, so API
loading, success, error, cancellation or duplicate POST behavior cannot be tested
against a real backend. No mocked API success was substituted.

Backend runtime verification was not performed. The accessible bundled Python
runtime lacks `fastapi`, `pydantic_settings`, `uvicorn` and `httpx`; discovery of
the registered system Python encountered an OS access error. No dependencies,
backend source or backend configuration were changed. Health and product API
availability findings are based on source inspection, not a live server test.
