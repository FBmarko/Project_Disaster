# Fault Lines — implementation and validation

Verified 2026-09-03. See [data-sources.md](data-sources.md) for exact source URLs,
license, citation, filter recipe and preserved-coordinate provenance.

## Scope and behavior

- `/fault-lines` uses actual province geometry and backend GEM active-fault geometry in inline SVG.
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
  real source ID, metadata, city-availability section and nearby-earthquake table.
- City relationships are not supplied and are never inferred. Nearby earthquake
  records come from the backend proximity endpoint; empty and error states remain distinct.
- Source geometry has no fault names for these records. “Adsız Fay Segmenti”
  plus original catalog ID is a neutral fallback, not a fabricated fault name.
- The archived 321-segment local dataset remains only for provenance, import and
  validation. It is not imported by the application and is never an API fallback.

## Commands and results

| Check | Result |
| --- | --- |
| `npm run validate:provinces` | PASS — 81/81; no missing or duplicate provinces |
| `npm run validate:faults` | PASS — 321 unique, scoped, finite, renderable source features |
| `npm run validate:faults -- node_modules/.cache/afet360/gem_active_faults.geojson` | PASS — all retained features, properties and coordinates deep-equal original source |
| `npm run build` | PASS — TypeScript and Vite production build |
| `npm run lint` | PASS — oxlint |
| `git diff --check` | PASS |

Current production bundle measurements are recorded in
[release-readiness.md](release-readiness.md). No new dependencies were added.

The fault validator also verifies its canonical asset hash, documented bounding
box, source IDs, safe unnamed fallback, invalid geometry rejection, multipart
paths, finite tooltip anchors and non-collapsing projected segments. Every
HomePage path, centroid and viewBox is identical to the pre-change baseline hash.

## Browser verification

Local Vite app tested in the Codex in-app Chromium browser:

- `/` and `/fault-lines` both open with the existing navigation.
- The historical local-data UI check rendered all 321 archived segments; current
  runtime rendering uses the records returned by the project backend.
- Pointer hover and click tested on `ME_TRCS001`; tooltip identifies that source
  record. Selection remains after leaving the map, and the tooltip disappears.
- Enter selects `ME_TRCS002`; Space selects `ME_TRCS003`.
- Native dropdown updates the selected line; clearing it restores the initial
  empty state. Current earthquake proximity integration is documented in
  [backend-integration.md](backend-integration.md).
- Sidebar opens/closes and reports `aria-current="page"` for Fay Hatları.
- Layout checked at 1440×900, 768×1024, 390×844 and 320×800; no page-level
  horizontal overflow. Details stack vertically on narrow screens.
- HomePage Ankara hover/focus still reports “Orta Risk” and fills `#F59E0B`.
- Browser console recorded no warnings or runtime errors in the checked flows.
- Source/build inspection confirms the archived fault asset does not enter a
  runtime chunk. The current page uses the project API and performs no third-party
  GEM request. External source links are attribution links followed only on click.

Responsive checks used browser viewport resizing, not physical touch hardware.
Screen-reader behavior was implemented through semantic markup but not tested
with a separate assistive-technology application.

## Historical implementation file inventory

Created:

- `docs/licenses/GEM-CC-BY-SA-4.0.txt`
- `docs/fault-lines-validation.md`
- `scripts/import-faults.ts`
- `scripts/validate-faults.ts`
- `src/types/fault.ts`
- `src/data/faultFeatures.ts`
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
