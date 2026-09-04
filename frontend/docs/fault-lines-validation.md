# Fault Lines — implementation and validation (historical Step 3 record)

Verified 2026-09-03. See [data-sources.md](data-sources.md) for exact source URLs,
license, citation, filter recipe and preserved-coordinate provenance.

## Scope and behavior

- `/fault-lines` uses actual province and GEM active-fault geometry in inline SVG.
- 321 source LineStrings / 3,787 original positions; the shared adapter and
  projector also support MultiLineString without joining separate parts.
- A 12px transparent hit layer sits below the visible strokes so direct line
  hits take precedence. Hover emphasizes the line and displays a source-ID tooltip.
- Clicking, Enter/Space or the native selection list selects exactly one segment.
  The selected stroke retains a white casing and thicker dark-red line after
  pointer leave. `aria-pressed`, focus outlines and a live selected-name status
  communicate the selection beyond color.
- The tooltip ignores pointer events and is positioned within the map container.
- The initial details state invites selection. Selecting a segment reveals its
  real source ID, city section and historical table (Tarih / Konum / Büyüklük).
- City and historical earthquake arrays are supplied data, never inferred.
  Current UI shows explicit backend-pending states; no details fixtures exist.
  Future development detail responses have a separate visible demo-data notice.
- Source geometry has no fault names for these records. “Adsız Fay Segmenti”
  plus original catalog ID is a neutral fallback, not a fabricated fault name.
- Existing Navbar, Sidebar, HomePage, risk data, province asset and other routes
  were not edited. The only shared change exposes the existing fitted lon/lat
  transform from `projectTurkeyMap.ts` (three added lines).

## Commands and results

| Check | Result |
| --- | --- |
| `npm run validate:provinces` | PASS — 81/81; no missing or duplicate provinces |
| `npm run validate:faults` | PASS — 321 unique, scoped, finite, renderable source features |
| `npm run validate:faults -- node_modules/.cache/afet360/gem_active_faults.geojson` | PASS — all retained features, properties and coordinates deep-equal original source |
| `npm run build` | PASS — TypeScript and Vite production build |
| `npm run lint` | PASS — oxlint |
| `git diff --check` | PASS |

The production JS bundle is about 692 KB (215 KB gzip). Vite reports its
non-fatal 500 KB chunk-size advisory because geographic assets are bundled.
No new dependencies were added.

The fault validator also verifies its canonical asset hash, documented bounding
box, source IDs, safe unnamed fallback, invalid geometry rejection, multipart
paths, finite tooltip anchors and non-collapsing projected segments. Every
HomePage path, centroid and viewBox is identical to the pre-change baseline hash.

## Browser verification

Local Vite app tested in the Codex in-app Chromium browser:

- `/` and `/fault-lines` both open with the existing navigation.
- All 321 accessible fault buttons and province borders render.
- Pointer hover and click tested on `ME_TRCS001`; tooltip identifies that source
  record. Selection remains after leaving the map, and the tooltip disappears.
- Enter selects `ME_TRCS002`; Space selects `ME_TRCS003`.
- Native dropdown updates the selected line; clearing it restores the initial
  empty state. At Step 3 both sections displayed pending text. Current earthquake proximity integration is documented in backend-integration.md.
- Sidebar opens/closes and reports `aria-current="page"` for Fay Hatları.
- Layout checked at 1440×900, 768×1024, 390×844 and 320×800; no page-level
  horizontal overflow. Details stack vertically on narrow screens.
- HomePage Ankara hover/focus still reports “Orta Risk” and fills `#F59E0B`.
- Browser console recorded no warnings or runtime errors in the checked flows.
- Source/build inspection confirms the fault asset is embedded locally via
  `?raw`; Step 3 had no runtime fetch/API client; the current page uses the project API. The two external UI links are
  attribution links only. No third-party network request interception was used.

Responsive checks used browser viewport resizing, not physical touch hardware.
Screen-reader behavior was implemented through semantic markup but not tested
with a separate assistive-technology application.

## Step 3 file inventory

Created:

- `docs/licenses/GEM-CC-BY-SA-4.0.txt`
- `docs/fault-lines-validation.md`
- `scripts/import-faults.ts`
- `scripts/validate-faults.ts`
- `src/types/fault.ts`
- `src/data/faultFeatures.ts`
- `src/data/turkeyFaults.ts`
- `src/data/turkey-active-faults.geojson`
- `src/data/turkey-active-faults.manifest.json`
- `src/components/map/projectFaultLines.ts`
- `src/components/map/FaultLinesMap.tsx`
- `src/components/map/FaultTooltip.tsx`
- `src/components/fault/FaultDetailsPanel.tsx`
- `src/components/fault/FaultCities.tsx`
- `src/components/fault/FaultEarthquakeTable.tsx`

Modified:

- `README.md`
- `docs/data-sources.md`
- `package.json`
- `src/components/map/projectTurkeyMap.ts`
- `src/pages/FaultLinesPage.tsx`

All paths above are relative to `frontend/`. No backend files are included.
