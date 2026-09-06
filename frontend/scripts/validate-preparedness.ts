/** Offline validation of the form boundary and memory-only profile lifecycle. */
import assert from 'node:assert/strict'
import { TURKEY_PROVINCES } from '../src/constants/provinces.ts'
import { createPreparednessState, preparednessReducer, preparePreparednessProfile, validatePreparednessDraft } from '../src/utils/preparednessDraft.ts'
import type { PreparednessDraft } from '../src/types/preparedness.ts'

let checks = 0
function check(name: string, run: () => void) {
  run()
  checks += 1
  console.log(`PASS: ${name}`)
}

const initial = createPreparednessState()
const draft: PreparednessDraft = {
  city: 'İstanbul', disasterType: 'EARTHQUAKE', householdSize: 4,
  hasChildren: true, hasElderlyPerson: false, hasPets: true,
}

check('Unanswered form cannot prepare a profile', () => {
  assert.equal(preparePreparednessProfile(initial.draft).ok, false)
  assert.equal(preparednessReducer(initial, { type: 'submit' }).preparedProfile, null)
  assert.deepEqual(Object.keys(validatePreparednessDraft(initial.draft)), ['city', 'hasChildren', 'hasElderlyPerson', 'hasPets'])
})
check('Exactly the canonical 81 provinces are accepted', () => {
  assert.equal(TURKEY_PROVINCES.length, 81)
  assert.equal(new Set(TURKEY_PROVINCES).size, 81)
  for (const city of TURKEY_PROVINCES) assert.equal(preparePreparednessProfile({ ...draft, city }).ok, true)
  for (const city of ['', 'Unknown', 'istanbul']) assert.equal(preparePreparednessProfile({ ...draft, city }).ok, false)
})
check('Only earthquake is supported', () => {
  for (const disasterType of ['', 'FLOOD', 'FIRE']) assert.equal(preparePreparednessProfile({ ...draft, disasterType }).ok, false)
})
check('All integer sizes 1–20 accepted; empty, fractional, nonfinite and out-of-range sizes rejected', () => {
  for (let householdSize = 1; householdSize <= 20; householdSize += 1) {
    assert.equal(preparePreparednessProfile({ ...draft, householdSize }).ok, true)
  }
  for (const householdSize of [null, 0, -1, 21, 1.5, NaN, Infinity, -Infinity]) {
    assert(validatePreparednessDraft({ ...draft, householdSize }).householdSize)
    assert.equal(preparePreparednessProfile({ ...draft, householdSize }).ok, false)
  }
})
check('Every boolean combination preserves deliberate yes/no choices', () => {
  for (const hasChildren of [true, false]) for (const hasElderlyPerson of [true, false]) for (const hasPets of [true, false]) {
    const complete = { ...draft, hasChildren, hasElderlyPerson, hasPets }
    assert.deepEqual(preparePreparednessProfile(complete), { ok: true, profile: complete })
  }
  for (const field of ['hasChildren', 'hasElderlyPerson', 'hasPets'] as const) {
    assert.equal(preparePreparednessProfile({ ...draft, [field]: null }).ok, false)
  }
})
check('Unexpected runtime input types fail validation', () => {
  for (const patch of [{ householdSize: '4' }, { hasChildren: 'false' }, { hasPets: 1 }, { hasElderlyPerson: undefined }, { city: null }]) {
    assert.equal(preparePreparednessProfile({ ...draft, ...patch } as unknown as PreparednessDraft).ok, false)
  }
})
check('Submit retains only a detached typed profile, never a guide or loading state', () => {
  const editing = preparednessReducer(initial, { type: 'change', draft })
  const submitted = preparednessReducer(editing, { type: 'submit' })
  assert.deepEqual(submitted, { draft, submitted: true, preparedProfile: draft })
  assert.notEqual(submitted.preparedProfile, draft)
  assert.deepEqual(preparednessReducer(submitted, { type: 'submit' }), submitted)
  assert.equal(initial.preparedProfile, null)
})
check('Editing any field clears the prepared profile while retaining other input', () => {
  const submitted = preparednessReducer({ ...initial, draft }, { type: 'submit' })
  for (const patch of [{ city: 'Ankara' }, { disasterType: '' }, { householdSize: 20 }, { hasChildren: false }, { hasElderlyPerson: true }, { hasPets: false }]) {
    const changed = preparednessReducer(submitted, { type: 'change', draft: { ...draft, ...patch } })
    assert.equal(changed.preparedProfile, null)
    assert.deepEqual(changed.draft, { ...draft, ...patch })
  }
})

import { ApiError } from '../src/api/client.ts'
import {
  buildBackendPayload,
  getPreparednessErrorMessage,
  parsePreparednessResponse,
} from '../src/api/preparedness.ts'

check('buildBackendPayload maps profile to snake_case payload with correct defaults and values', () => {
  const payload = buildBackendPayload({
    city: 'İzmir',
    disasterType: 'EARTHQUAKE',
    householdSize: 3,
    hasChildren: true,
    hasElderlyPerson: false,
    hasPets: true,
  })
  assert.deepEqual(payload, {
    disaster_type: 'earthquake',
    city: 'İzmir',
    language: 'tr',
    household_size: 3,
    has_children: true,
    has_elderly_person: false,
    has_pets: true,
  })

  // Whitespace-only city maps to undefined
  const emptyCityPayload = buildBackendPayload({
    city: '   ',
    disasterType: 'EARTHQUAKE',
    householdSize: 1,
    hasChildren: false,
    hasElderlyPerson: false,
    hasPets: false,
  })
  assert.equal(emptyCityPayload.city, undefined)
})

check('parsePreparednessResponse correctly transforms backend response to camelCase contract', () => {
  const sampleBackendResponse = {
    disaster_type: 'earthquake',
    city: 'İzmir',
    language: 'tr',
    generated_by_ai: true,
    guide: {
      summary: 'İzmir için hazırlık özeti.',
      priorities: ['Deprem çantası', 'Bina güvenliği'],
      emergency_kit: ['Su', 'Düdük', 'Fener'],
      communication_plan: ['Şehir dışı irtibat kişisi'],
      special_needs: ['Bebek bezi'],
      important_notes: ['Resmi açıklamaları takip edin.'],
    },
    disclaimer: 'Bu rehber bilgilendirme amaçlıdır.',
  }

  const parsed = parsePreparednessResponse(sampleBackendResponse)
  assert.equal(parsed.disasterType, 'earthquake')
  assert.equal(parsed.city, 'İzmir')
  assert.equal(parsed.language, 'tr')
  assert.equal(parsed.generatedByAi, true)
  assert.equal(parsed.disclaimer, 'Bu rehber bilgilendirme amaçlıdır.')
  assert.equal(parsed.guide.summary, 'İzmir için hazırlık özeti.')
  assert.deepEqual(parsed.guide.priorities, ['Deprem çantası', 'Bina güvenliği'])
  assert.deepEqual(parsed.guide.emergencyKit, ['Su', 'Düdük', 'Fener'])
  assert.deepEqual(parsed.guide.communicationPlan, ['Şehir dışı irtibat kişisi'])
  assert.deepEqual(parsed.guide.specialNeeds, ['Bebek bezi'])
  assert.deepEqual(parsed.guide.importantNotes, ['Resmi açıklamaları takip edin.'])

  // Assert legacy fields (before, during, after) are absent
  assert.equal('before' in parsed.guide, false)
  assert.equal('during' in parsed.guide, false)
  assert.equal('after' in parsed.guide, false)
})

check('parsePreparednessResponse rejects malformed or incomplete backend structures', () => {
  assert.throws(() => parsePreparednessResponse(null))
  assert.throws(() => parsePreparednessResponse({}))
  // Missing guide
  assert.throws(() => parsePreparednessResponse({
    disaster_type: 'earthquake',
    language: 'tr',
    generated_by_ai: true,
    disclaimer: 'test',
  }))
  // Missing disclaimer
  assert.throws(() => parsePreparednessResponse({
    disaster_type: 'earthquake',
    language: 'tr',
    generated_by_ai: true,
    guide: {
      summary: 'ö', priorities: [], emergency_kit: [],
      communication_plan: [], special_needs: [], important_notes: [],
    },
  }))
  // Non-array items in guide
  assert.throws(() => parsePreparednessResponse({
    disaster_type: 'earthquake',
    language: 'tr',
    generated_by_ai: true,
    disclaimer: 'test',
    guide: {
      summary: 'ö',
      priorities: 'not-an-array',
      emergency_kit: [], communication_plan: [],
      special_needs: [], important_notes: [],
    },
  }))
})

check('getPreparednessErrorMessage maps HTTP status codes and network errors correctly', () => {
  assert.equal(
    getPreparednessErrorMessage(new ApiError(422)),
    'Girdiğiniz bilgiler geçersiz. Lütfen form alanlarını kontrol ediniz.',
  )
  assert.equal(
    getPreparednessErrorMessage(new ApiError(429)),
    'Çok fazla istek gönderildi. Lütfen bir süre bekleyip tekrar deneyiniz.',
  )
  assert.equal(
    getPreparednessErrorMessage(new ApiError(502)),
    'Yapay zeka servisi yanıt veremedi. Lütfen biraz sonra tekrar deneyiniz.',
  )
  assert.equal(
    getPreparednessErrorMessage(new ApiError(503)),
    'Hazırlık rehberi servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyiniz.',
  )
  assert.equal(
    getPreparednessErrorMessage(new ApiError(500)),
    'Bağlantı kurulamadı. Lütfen internet bağlantınızı ve servis durumunu kontrol ediniz.',
  )
  assert.equal(
    getPreparednessErrorMessage(new Error('Network error')),
    'Bağlantı kurulamadı. Lütfen internet bağlantınızı ve servis durumunu kontrol ediniz.',
  )
  const timeoutErr = new Error('Request timed out')
  timeoutErr.name = 'TimeoutError'
  assert.equal(
    getPreparednessErrorMessage(timeoutErr),
    'Hazırlık rehberinin oluşturulması beklenenden uzun sürdü. Lütfen tekrar deneyiniz.',
  )
})

import { DEFAULT_POST_TIMEOUT_MS } from '../src/api/client.ts'
import { PREPAREDNESS_TIMEOUT_MS } from '../src/api/preparedness.ts'

check('Timeout configurations are bounded, finite, and AI timeout exceeds provider window', () => {
  assert.equal(typeof DEFAULT_POST_TIMEOUT_MS, 'number')
  assert.equal(Number.isFinite(DEFAULT_POST_TIMEOUT_MS), true)
  assert.equal(DEFAULT_POST_TIMEOUT_MS, 20_000)

  assert.equal(typeof PREPAREDNESS_TIMEOUT_MS, 'number')
  assert.equal(Number.isFinite(PREPAREDNESS_TIMEOUT_MS), true)
  assert.equal(PREPAREDNESS_TIMEOUT_MS, 45_000)

  // AI timeout must exceed backend Gemini 30.0s deadline + transport margin
  assert.equal(PREPAREDNESS_TIMEOUT_MS > 30_000, true)
  assert.equal(PREPAREDNESS_TIMEOUT_MS >= DEFAULT_POST_TIMEOUT_MS, true)
})

console.log(`OK: ${checks} preparedness checks passed. No services, generated results or network used.`)
