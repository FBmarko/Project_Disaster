# Preparedness Guide — Step 6

Route: `/preparedness-guide`. The primary sidebar now uses Hazırlık Rehberi in
place of Simülasyon Sonuçları. Step 9 removes the cancelled `/simulation-results`
route and placeholder page. Assembly Areas is available at `/assembly-areas`.
See [backend-integration.md](backend-integration.md) for the current API audit.

## Current form lifecycle

- `PreparednessGuidePage` composes the form and reusable results area.
- `PreparednessForm` uses native selects, a number input, and `BooleanChoice`
  radio groups with labels, legends, visible keyboard focus, linked inline
  errors and a submit error announcement. An invalid submit focuses the first
  invalid control.
- `PreparednessDraft` distinguishes unanswered booleans from `false` and an
  empty number from zero. `validatePreparednessDraft` verifies canonical city
  membership, the earthquake type, integer household size 1–20, and all choices.
- `preparePreparednessProfile` creates the six-field `PreparednessProfile`:
  `city`, `disasterType: 'EARTHQUAKE'`, `householdSize`, `hasChildren`,
  `hasElderlyPerson`, and `hasPets`. The province select reuses
  `constants/provinces.ts` without fetching or duplicating geographic data.
- A valid submit retains a detached profile in page memory. Any edit clears the
  prepared profile. Reloading or leaving the page discards it. There is no
  logging, local storage, transmission, timer, artificial delay or generated
  guidance. Product copy explains that guide creation is currently unavailable.

## Future integration boundary

The required architecture is **Frontend → Project Backend → AI Provider/Model →
Project Backend → Frontend**. The frontend must never call a provider directly.
No AI SDK, provider credentials or Vite AI key is introduced. The current backend
now registers `POST /api/v1/ai/preparedness-guide`, but its production provider
dependency returns None and valid calls return 503. Only tests override it with a
stub. The local form remains unconnected until real generation is available.

The strict request accepts only `disaster_type`, optional `city` and `language`;
extra household fields are rejected. The response uses `summary`, `before`,
`during`, `after`, `emergency_kit`, `important_notes` and a backend disclaimer.
It does not supply household personalization or a separate communication plan.
The UI arrays below remain local display types, not backend DTOs.

`PreparednessGuideResults` expects a `PreparednessGuide | null`, with exactly:

| Field | Type | Display heading |
| --- | --- | --- |
| `priorities` | `string[]` | Öncelikler |
| `emergencyKit` | `string[]` | Afet Çantası |
| `communicationPlan` | `string[]` | İletişim Planı |
| `specialNeeds` | `string[]` | Özel İhtiyaçlar |

`null` means no guide exists. `GuideSection` displays structured lists or explicit
empty sections. Strings render as React text, not HTML. No fixture is wired into
the page. `PreparednessSafetyNotice` is always present, with or without results.

When production generation and the product schema are aligned, add an adapter at the page/service
boundary, validate responses at runtime, and supply the four structured arrays.
Implement real loading, error and cancellation states then. Clear stale results
when the profile changes and prevent responses for older profiles from replacing
newer results. Never pass one unstructured model paragraph directly to the UI.
The current backend does not accept children, elderly-person or pet flags. The
frontend must not imply that these choices personalize generated suggestions.
Later fields can extend the profile and draft without changing the section
renderer. Sensitive or medical questions are outside this task.

## Future backend/model safety requirements

Backend/model system instructions and response validation must prevent:

- earthquake prediction claims;
- guaranteed outcomes or unsupported scientific certainty;
- impersonation of an official authority;
- advice that replaces emergency authority guidance;
- medical diagnosis.

These safeguards belong in the backend integration, not frontend prompt
strings. The permanent product notice directs users to AFAD and relevant official
authorities. Do not frame generated guidance as official advice.

## Validation

Run `npm run validate:preparedness` for boundary values, all canonical cities,
unanswered and malformed fields, every boolean combination, and profile lifecycle.
Also run the existing province, fault and simulation validations, build and lint.
Browser checks should cover invalid/valid submit, input changes, keyboard focus,
the sidebar, existing routes, and widths 1440, 768, 390 and 320 pixels.
