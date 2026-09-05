# Assembly Areas — backend integration

`/assembly-areas` appears after Hazırlık Rehberi in the sidebar.

## Contract and data semantics

`GET /api/v1/assembly-areas/nearby` accepts `lat`, `lon`, `radius_km` (>0..200) and `limit` (1..100). The page requests at most 100 records and displays the backend `truncated` flag. Source: OpenStreetMap community-mapped emergency assembly points, ODbL 1.0, not official AFAD areas. Metadata attribution and source timestamp appear even for an empty successful response. An AFAD operator tag is never interpreted as verification. Coverage can be incomplete or facility-specific.

`src/api/assemblyAreas.ts` validates the response and explicitly maps UUIDs, source IDs, nullable name/ref/operator and distance to `AssemblyArea[]`. It rejects malformed coordinates and duplicate IDs. No province, district, address or capacity is fabricated. The historical `ASSEMBLY_AREAS=[]` constant and region validator remain for existing validations; neither supplies runtime results.

## Search and privacy

The API has no administrative text query. The form now accepts explicit coordinates and an adjustable radius (default 5 km), or requests current location after Konumumu Kullan. Input edits clear prior results/selection and cancel pending location/network requests. Loading disables submission; errors allow an explicit retry. Keyed requests and AbortController prevent late responses from replacing newer state.

A single `getCurrentPosition` call retains its ten-second timeout, no watch/automatic retry and existing denial/timeout/unavailable states. The button notice explains that coordinates are transmitted for the requested search. Coordinates remain in page memory: no localStorage, sessionStorage, cookies or frontend logs. GET parameters necessarily contain the search coordinates; server/proxy access-log retention is a deployment responsibility. Requests use no-store, omit credentials and no-referrer. Directions URLs never include the user's origin.

## Map and list

The existing Google Maps wrapper, environment key, loading boundary and missing-key state are retained. Point geometry maps directly from `[lon,lat]` to marker coordinates. Polygon rings are displayed as Google Maps polygons, including holes, with no centroid, altered boundary or invented entrance. Selection works from point markers, polygons and list cards; selecting a polygon fits its actual bounds. List actions provide keyboard access to polygon selection. Overlays/listeners are removed when replaced or unmounted.

Cards show only available fields and backend geodesic distance (not walking distance). Point records offer Haritada Göster and a destination-only Google Maps Yol Tarifi link. Polygon records offer Haritada Göster and explain why no directions target can be supplied without an entrance point. The UI never guarantees route safety.

Initial, loading, success, honest empty and error states are separate. Errors never fall back to fixture locations. Empty results do not claim absence of official assembly areas. The permanent official-authority safety notice remains.

## Validation

`validate:assembly` preserves the existing coordinate/directions/geolocation cancellation checks and historical region validation. `validate:api` adds real-contract mapping boundaries for Point/Polygon, UUIDs, source metadata, empty collections, malformed geometry and absence of guessed destinations. Synthetic test fixtures never ship in the application. See [backend-integration.md](backend-integration.md) for current live/browser test results and environment setup.
