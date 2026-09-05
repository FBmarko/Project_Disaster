# Frontend release readiness and dependency handoff

Verified 2026-09-05 on `feature/afet360-frontend`. This document describes the
current product boundary for frontend review and merge.

## Frontend complete

- Six routed pages, shared Navbar/Sidebar navigation and responsive layouts.
- Global light/dark theme with system-default resolution, explicit persisted
  choice and early document initialization.
- Accessible SVG province and fault maps, form controls, selection states,
  visible focus, loading, error, empty and retry states.
- Real project-API integration for GEM faults, selected-fault earthquake
  proximity and nearby assembly areas, with runtime response validation and
  request cancellation.
- Local-only scenario and preparedness drafts that create no fabricated results,
  call no external AI provider and persist no location or household data.
- Route-level chunks for all six pages. Province geometry stays local to the Home
  route; the archived fault dataset is validation/provenance only; Google Maps
  code loads only from the Simulation and Assembly routes when a key is present.

## Backend and product contract dependencies

These are integration dependencies rather than frontend defects:

1. **Province hazard/risk contract:** backend hazard endpoints expose modeled PGA
   points, not scientifically defined province LOW/MEDIUM/HIGH classifications.
   The Home map therefore retains clearly labelled development UI data and does
   not derive categories from PGA.
2. **Fault names:** some source/backend records lack usable human-readable names.
   The UI preserves supplied names and otherwise uses the neutral “Adsız Fay
   Segmenti” fallback; a richer label requires authoritative source metadata.
3. **Earthquake availability:** the proximity endpoint is integrated, but the
   local database may be empty until bounded AFAD ingestion is available and
   populated. The UI treats this as an honest empty result.
4. **Production AI provider:** the preparedness endpoint is registered, but its
   production provider is unavailable. The frontend does not call providers or
   generate replacement guidance.
5. **Preparedness contract:** the current backend request has no household size,
   children, elderly-person or pet fields, and its response structure differs
   from the product UI sections. Product and backend contracts must be aligned
   before the existing local profile can be submitted.
6. **Assembly dataset:** nearby-area integration is complete, but useful results
   depend on an approved imported dataset. The frontend shows distinct empty and
   unavailable states and never supplies fallback locations.
7. **Simulation service:** no project simulation endpoint or scientific result
   contract exists. The page prepares and validates scenario inputs only.

## Final QA evidence

- Before route splitting, the main JavaScript chunk was 558.18 kB (188.59 kB
  gzip) and triggered Vite's 500 kB advisory.
- After route splitting, the entry chunk is 233.67 kB (75.41 kB gzip). The
  largest JavaScript chunk is the Home-only province geometry at 243.71 kB
  (88.45 kB gzip), and no chunk-size advisory remains.
- Google Simulation and Assembly map implementations remain separate 1.89 kB and
  3.51 kB chunks. The local fault archive is absent from production chunks.
- All seven frontend validators, the production build and lint pass. The local
  project API returned 722 real fault records and a valid empty proximity result
  for the checked segment.
- All six routes passed light and dark browser checks at 1440, 1024, 768, 390 and
  320 px with no page-level horizontal overflow or console warnings/errors.

## Merge checks

Run all `validate:*` scripts in `package.json`, then `npm run build` and
`npm run lint`. Browser QA covers all six routes in both themes at 1440, 1024,
768, 390 and 320 px, including navigation, forms, map states, focus, overflow,
console output and request behavior. Current measured bundle output and final Git
state belong in the merge report so they reflect the exact release commit.
