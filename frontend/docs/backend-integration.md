# Updated backend API audit and frontend integration

Audited 2026-09-04 against `aa0520f` (backend `04b1389`), before editing frontend integration code. This replaces the obsolete health-only audit. Registered routers, endpoint implementations, schemas, query services/repositories and API tests take precedence over stale backend README phase notes.

## Pre-implementation matrix

All paths below include the default `/api/v1` prefix. GETs have no request body. Geospatial routes require PostgreSQL/PostGIS, applied migrations and imported data for populated success responses; endpoint availability is distinct from local infrastructure availability.

| Feature | Actual endpoints | Method | Status | Frontend integration decision |
| --- | --- | --- | --- | --- |
| Home / hazard | `/api/v1/earthquake-hazards`, `/api/v1/earthquake-hazards/dataset`, `/api/v1/earthquake-hazards/nearest` | GET | PARTIALLY AVAILABLE for Home | No province classification exists. Retain existing explicitly labelled development visualization; do not aggregate PGA nodes into risk categories. |
| Faults | `/api/v1/fault-lines`, `/api/v1/fault-lines/nearby`, `/api/v1/fault-lines/{fault_id}` | GET | AVAILABLE | Use returned MultiLineString geometry and UUIDs as canonical runtime records, including actual names/type/activity. No joins to the different local GEM/EMME subset. |
| Earthquake events | `/api/v1/earthquakes`, `/api/v1/earthquakes/recent-major`, `/api/v1/earthquakes/{event_id}` | GET | AVAILABLE | Use the selected-fault proximity endpoint below in the existing details panel. |
| Fault proximity | `/api/v1/fault-lines/{fault_id}/earthquakes` | GET | AVAILABLE | Label Yakındaki Depremler; geographic proximity never implies causal fault rupture. |
| Simulation | None | — | NOT AVAILABLE | Existing local scenario form unchanged. No results page, POST, polling or fabricated results. |
| Preparedness | `/api/v1/ai/preparedness-guide` | POST | PARTIALLY AVAILABLE | Registered contract but production provider dependency always returns None/503. Keep local profile UI; no test stub exposed as AI. Household fields have no request equivalent. |
| Assembly | `/api/v1/assembly-areas`, `/api/v1/assembly-areas/nearby`, `/api/v1/assembly-areas/dataset` | GET | AVAILABLE | Coordinate/radius searches; preserve Point and Polygon geometries, attribution and non-official community-data meaning. No administrative text search. |
| Health | `/api/v1/health` | GET | AVAILABLE | Runtime verification only. No database dependency. |

## Actual contracts

- **Health:** no parameters; 200 `{status, service, version}` strings. No endpoint-specific error schema.
- **Fault list:** optional `bbox=min_lon,min_lat,max_lon,max_lat`, `fault_type`, `limit` 1–2000 (1000 default). Nearby uses required `latitude`, `longitude`, `radius_km` >0..500 and `limit` 1–100 (20 default). Detail uses UUID `fault_id`. GeoJSON FeatureCollection or Feature; geometry is MultiLineString `[lon,lat]`. Properties: UUID `id`, `source`, `source_feature_id`, nullable `name`, `segment_name`, `fault_type`, `activity_status`, `distance_km`. Collection metadata: `count`, `source`, `license`, `attribution`, `disclaimer`. 200 including empty collections, 422 invalid query/UUID, 404 absent detail. No cities field. Full-list query has no offset or total count; a response at the limit must not be represented as exhaustive.
- **Earthquake list:** optional `min_magnitude`/`max_magnitude` -2..10, `magnitude_type` (max 20 characters), timezone-aware `start_time`/`end_time`, `bbox`, `limit` 1–1000 (100 default), `offset` >=0. Recent-major: `days` 1–3650 (365 default), `min_magnitude` 0..10 (5 default), optional `max_distance_km` >0..500, `limit` 1–500 (100 default), `offset` >=0. Detail uses UUID `event_id`. 200, 422, or 404 absent detail.
- **Selected-fault earthquakes:** UUID `fault_id`; required `max_distance_km` >0..500; `min_magnitude` -2..10 (5 default), timezone-aware start/end, `limit` 1–500 (100 default), `offset` >=0, `order_by=recent|distance`. 200 including empty, 422 invalid input, 404 absent fault. Point GeoJSON properties include `id`, `source`, `source_event_id`, `occurred_at`, `depth_km`, `magnitude`, `magnitude_type`, nullable `location_name`, country/province/district/neighborhood; proximity adds `distance_to_fault_km`, `nearest_fault_id`, `nearest_fault_source_feature_id`, `association_method=spatial_proximity`, `proximity_disclaimer`. Metadata identifies the target fault, radius, AFAD attribution, GEM attribution/license and scientific disclaimer. Data is a locally synchronized AFAD snapshot, not guaranteed real-time. No frontend spatial association is calculated.
- **Hazard dataset:** no query; provenance including source/version/model, PGA metric in g, return period 475 years, 10% exceedance in 50 years, reference rock Vs30 800 m/s, DOIs/license, geographic scope/count/checksum. **Nearest:** required `lat`, `lon` within [24..46°E,34..44°N]; Point Feature with `pga_g`, `distance_to_source_node_km`, `source_record_id`, `semantics=nearest_source_node`, provenance. **Collection:** required bbox wholly within that scope, `limit` 1–2000 (1000 default), `offset` >=0; Point features with `id`, `source_record_id`, `pga_g`; metadata includes `count`, bbox, limit, offset, `has_more` and scientific provenance. 200 (collection may be empty), 422 invalid/out-of-scope coordinates, 404 nearest with no node, 503 missing dataset. These are discrete modeled seismic hazard values, not province risk, building safety or local soil amplification.
- **Assembly list:** optional bbox and `limit` 1–2000 (1000 default). **Nearby:** required `lat`, `lon`, `radius_km` >0..200; `limit` 1–100 (20 default). **Dataset:** no query; provenance and Point/Polygon counts. GeoJSON FeatureCollection with UUID-string feature IDs, native Point or Polygon coordinates; properties `source_feature_id`, nullable `name`, `ref`, `operator`, and nearby-only `distance_km`. No address, province, district, neighborhood, capacity, official verification or entrance coordinate. Metadata: `returned_count`, `truncated`, `source`, `provider`, `source_classification`, `license`, `attribution`, `source_reference`, snapshot/source timestamps, SHA-256 and disclaimer. 200 including empty, 422 invalid query, 503 missing dataset. Polygon distance is to geometry, zero inside; not walking distance. OSM community records may be incomplete or facility-specific and are not official AFAD locations, even when operator says AFAD.
- **Preparedness request:** `{disaster_type: earthquake|flood|fire, city?: string|null, language?: tr|en}`; city trimmed, 1–80 characters, language defaults tr, extra fields forbidden. No household size/children/elderly/pets fields. **Response:** `{disaster_type, city, language, generated_by_ai, guide, disclaimer}`. Guide: summary 10–600 chars; before/during/after each 1–8 strings of 3–300 chars; emergency_kit 1–12 strings of 2–200 chars; important_notes 0–6 strings of 3–300 chars. 200 only with a working provider; 422 invalid request, 502 provider/malformed output, 503 unavailable. No DB needed. `app/integrations/ai/dependencies.py` always returns None; tests alone override it with `tests/fakes/ai.py`. Before/during/after cannot safely be relabelled communicationPlan. No transport/mapper is wired until production generation and product expectations can be reconciled.

Unhandled database connection failures can produce server errors; frontend must show friendly Turkish errors rather than raw details.

## Evidence

Read `backend/app/api/v1/router.py`, all six endpoint modules, schemas `fault_line_api.py`, `earthquake_api.py`, `hazard_api.py`, `assembly_api.py`, `ai.py`, query services and repositories, preparedness service/provider dependency, API tests, README, `.env.example`, pyproject and root Docker Compose. Full backend simulation/scenario searches found no simulation route; magnitude/depth/radius are event or proximity fields, not simulation APIs. Backend README still says assembly API is absent in its older phase section; current router/source/tests prove it is exposed. Backend documentation was not edited.

## Implemented frontend behavior

- `src/api/client.ts`: native fetch, `VITE_API_BASE_URL`, validated JSON parsers, sanitized HTTP errors, explicit AbortSignal and a 20-second timeout. No credentials, browser caching or referrer in API requests. Missing base URL is an error, not a request to an assumed origin.
- `src/api/faults.ts`: collection query with documented regional bbox `24,34,46,44` and limit 2000. Backend UUID is the UI identity and proximity path parameter; `source_feature_id` is the display catalog identity. Geometry is transferred unchanged. No local/backend record join or duplicate geometry set. Local archived GEM assets and their integrity checks remain unchanged; they are never API-error fallbacks. Returned names, classification and activity appear in the selected panel. Cities remain explicitly unavailable.
- `src/api/earthquakes.ts`: selected-fault proximity query, max distance 25 km, minimum magnitude 5, newest-first, first 100 records. The UI states the filters and warns when the limit is reached. Date/time is labelled UTC; magnitude scale, depth and distance are preserved. The response must match the selected fault and declare spatial proximity. AFAD/GEM attribution and the non-causal notice are displayed even for empty results.
- `src/api/assemblyAreas.ts`: explicit coordinate/radius search with limit 100; truncation is surfaced. No unsupported administrative parameters. Full Point/Polygon mapping, null metadata, OSM attribution/source date, list/marker/polygon selection, and point-only destination links. Polygon bounds are preserved; no centroid or entrance is invented. See [assembly-areas.md](assembly-areas.md).
- `useApiResource` keys results to the current selection/search, aborts replaced/unmounted requests and suppresses late responses. All connected views provide loading, populated success, empty and friendly Turkish error states with retry. Edits clear assembly results; search buttons disable during a request. There are no integrated POSTs.
- Home province data remains explicitly labelled development UI data. Simulation
  and Preparedness remain local drafts, global light/dark theme applies to all
  routes, and each page is lazy-loaded. No production AI provider exists; the
  household schema mismatch is documented above. No hazard conversion,
  simulation results, AI output or emergency locations are fabricated.

## Environment and local operation

`VITE_API_BASE_URL` is the project backend root **before** `/api/v1` (or a same-origin proxy prefix). No origin is hard-coded in components. Backend currently has no CORS middleware. For local development/preview, an optional Vite proxy maps `/backend` to server-only `API_PROXY_TARGET`; set `VITE_API_BASE_URL=/backend` and set that target to the actual running local backend origin in ignored `.env.local`. Production needs its own reverse proxy or correctly configured backend CORS; the Vite development server is not production hosting.

`.env.example` contains only the required public `VITE_API_BASE_URL` and
`VITE_GOOGLE_MAPS_API_KEY` names, with blank values. Optional local-only
`API_PROXY_TARGET` and production `VITE_GOOGLE_MAPS_MAP_ID` settings remain
documented without placeholder entries. No AI credentials or new frontend
packages were added. Local ignored environment files remain uncommitted.

The final frontend completion boundary and seven outstanding backend/product
dependencies are summarized in [release-readiness.md](release-readiness.md).

## Runtime and validation results

- On 2026-09-05 the local project API health endpoint returned 200. The regional
  fault query returned 722 real records; the selected record had no source name,
  used the neutral fallback, and its proximity query returned a valid empty
  collection. The live Fault page rendered all 722 segments.
- The assembly request reached the integrated endpoint and produced the friendly
  unavailable/error state with retry and zero fallback records. Editing cleared
  it, and leaving during a new request produced no stale page update.
- All seven frontend validators, production build and lint passed. The fault
  validator covers the preserved local archive; API validation covers current
  response contracts. No test fixture is part of runtime behavior.
- All six routes passed browser checks in both themes at 1440, 1024, 768, 390 and
  320 px with one h1, no page overflow and a clean console. Sidebar Escape,
  theme keyboard operation/persistence, map keyboard selection, form validation,
  retry and navigation cancellation were exercised.
- No Google Maps key was configured, so live provider map/marker interaction was
  not claimed. Both map routes rendered their missing-key states in both themes,
  and no Google script loaded. No real geolocation permission was requested.
