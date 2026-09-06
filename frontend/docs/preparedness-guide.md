# Preparedness Guide

Route: `/preparedness-guide`. The sidebar label is Hazırlık Rehberi and Assembly
Areas is available at `/assembly-areas`. See
[backend-integration.md](backend-integration.md) for the current API audit.

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

## Integration architecture

The architecture is **Frontend Form → AFET360 Backend → Gemini Provider → Structured Pydantic Output → Frontend Results UI**.
The frontend never calls an AI provider directly. No AI SDK, provider credentials or Vite AI key is exposed on the frontend.
All AI communication passes through `POST /api/v1/ai/preparedness-guide`.

The request payload accepts `disaster_type`, optional `city`, `language`, and household profile fields:
`household_size` (1–20), `has_children`, `has_elderly_person`, and `has_pets`. Extra fields are forbidden.

The structured response uses `disaster_type`, `city`, `language`, `generated_by_ai`, `guide`, and `disclaimer`.
`PreparednessGuide` contains:

| Field | Type | Display heading |
| --- | --- | --- |
| `summary` | `string` | Hazırlık Özeti |
| `priorities` | `string[]` | Öncelikler |
| `emergencyKit` | `string[]` | Acil Durum Çantası |
| `communicationPlan` | `string[]` | İletişim Planı |
| `specialNeeds` | `string[]` | Özel İhtiyaçlar |
| `importantNotes` | `string[]` | Önemli Notlar |

`null` means no guide exists yet. `GuideSection` displays structured lists or explicit
empty sections. Strings render as React text, not HTML. `PreparednessSafetyNotice` is always present, with or without results, displaying the backend-controlled disclaimer.

The page and API client implement complete loading, error and cancellation states. Clear stale results
or errors when the draft changes, and abort pending requests when re-submitting or unmounting. Never pass unstructured model paragraphs directly to the UI.

## Backend/model safety requirements

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
