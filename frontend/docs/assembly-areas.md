# Assembly Areas — Step 7

`/assembly-areas` is linked after Hazırlık Rehberi in the primary sidebar. The
Simulation Results page and all existing page behaviors remain unchanged.

## Data boundary

`ASSEMBLY_AREAS` is an explicitly empty `readonly AssemblyArea[]`. No real or
fictional assembly locations, addresses, official coordinates, district datasets,
neighborhood datasets, distance values, capacity estimates or safety scores have
been added. There are no fixture records behind the UI.

`AssemblyArea` contains `id`, `name`, `province`, `district`, optional
`neighborhood`/`address`, and finite latitude/longitude coordinates. It is a local
display model, not a backend contract. Invalid coordinates are excluded from map
markers, selection and directions actions. Optional blank details are omitted.

Future integration must follow **Frontend → Project Backend → Approved
Assembly-Area Source → Project Backend → Frontend**. No transport, endpoints,
AFAD/e-Devlet/municipality integration, scraping, Google Places, Search, geocoding
or Directions API is implemented. Verify provenance, freshness, unique IDs and
coordinate validity before passing real records to the components. Associate
results with their search and ignore stale responses. Do not convert a lack of
available data into a claim that a region has no assembly areas.

## Search and privacy

`AssemblyAreaSearch` is a discriminated union:

- `CURRENT_LOCATION`: `latitude`, `longitude`;
- `REGION`: canonical `province`, optional `district` and `neighborhood` strings.

The manual form reuses the existing 81-province list. Province is required. No
district/neighborhood dataset exists in the project, so these are optional,
trimmed text fields bounded to 100 characters. Changing province clears both
refinements. These fields can later become approved backend-driven dropdowns.
Submitting prepares a page-state search only; it does not geocode the region or
move the map to invented coordinates. An edit clears the preceding search and
selected area. Empty-state copy distinguishes initial selection from unavailable
verified information after selection.

The geolocation API is invoked only by Konumumu Kullan. It uses a single
`getCurrentPosition` call with a ten-second timeout and supports loading,
success, denial, unavailable, timeout and unsupported-browser states. There is
no `watchPosition`, automatic retry or page-load permission request. Cancellation
ignores callbacks after manual edits, replacement requests or unmounting.

Precise coordinates are kept only in page memory. There is no storage, cookie,
logging or project-backend transmission. Leaving/reloading clears the search.
Google Maps naturally receives the camera/marker positions needed to display a
user-requested location when configured. No user-origin coordinates are added to
external directions URLs. Map instances are not cached across route unmounts.

## Maps and results

The assembly map follows the existing SimulationPage architecture: the same
installed `@vis.gl/react-google-maps` wrapper, lazy chunk, `APIProvider` quarterly
version, Turkish locale, Turkey bounds/zoom, environment-based key/map ID,
AdvancedMarker/Pin, authentication callback, real loading timeout and render
boundary. Existing map configuration is imported from `constants/simulation.ts`;
the simulation implementation is untouched. The assembly map has a separate ID
and no map-click search handler. Only `VITE_GOOGLE_MAPS_API_KEY` supplies the key;
no key or new dependency was added.

Missing-key, load, authentication and render errors stay inside the map panel.
The form, results empty state, notice and navigation remain usable. No Google
wrapper chunk is loaded without a key. The initial camera fits Turkey.

`AssemblyAreaList`, `AssemblyAreaCard` and `AssemblyAreaEmptyState` accept empty
or future real results. Selection uses `selectedAreaId`, resolved against the
source rather than duplicating an area object. Selected cards show a check and
“Seçili alan”; a live region announces the selected name. Cards show available
details. Selecting a marker selects its card; Haritada Göster selects the area
and pans/zooms the map without navigation. Repeating the action refocuses the map.

The sole user marker is a blue circular location icon. Future area markers are
red pins. A selected area uses a check glyph, larger pin and selected title, so
selection does not depend on color alone. No area markers are rendered today.

Yol Tarifi appears only with valid destination coordinates. It opens a standard
[Google Maps directions URL](https://developers.google.com/maps/documentation/urls/get-started#directions)
in a new tab with `noopener noreferrer`. There is no Directions API or distance
calculation. The official-information safety notice is always visible.

## Validation

`npm run validate:assembly` covers the empty source, all 81 provinces, manual
validation, optional text boundaries, finite/in-range coordinates, directions
URLs, all geolocation outcomes, one-shot callbacks and cancellation. Its numeric
boundary inputs are mathematical test values, never named emergency locations
or rendered results. No large test framework was added.

Run all existing validation scripts plus build and lint. Review `/assembly-areas`
at 1440, 768, 390 and 320px, check keyboard/form navigation and existing routes.
Without a real Maps key and approved records, live marker interaction cannot be
claimed as tested.

### Step 7 verification

- Province, fault, simulation, preparedness and assembly validation scripts: passed.
- Build and lint: passed. Vite retains its advisory about the existing large main
  bundle; the new Google map implementation is loaded as a separate lazy chunk.
- Removed the unused `ArrowRight` import from the already-committed About header
  to fix its TS6133 build error. No About markup or behavior changed.
- Browser: route loads, missing-key fallback is contained, all 81 province options
  plus the placeholder exist, invalid search focuses the province, optional text
  is preserved/trimmed on submission, and changing province clears refinements.
- Browser: geolocation starts after the button click, shows loading, and reaches
  the timeout state in this environment. No request occurs on initial load or
  route return. Denial, unsupported, unavailable, successful callbacks and
  cancellation were checked offline; a real permission-denied dialog and successful
  live location lookup were not exercised.
- Responsive: 1440, 768, 390 and 320px passed DOM overflow checks and visual review.
  Desktop uses a dominant map left/search right; smaller layouts put map first,
  search next, then results. Native keyboard focus and mobile controls work.
- Sidebar order and active state passed; Simulation Results is absent. Existing
  home, faults, simulation, preparedness and About routes load. No browser console
  errors or warnings were observed.
- No real Maps key or approved records were available. Live Google map loading,
  user/area marker interaction and external directions navigation were not tested.
