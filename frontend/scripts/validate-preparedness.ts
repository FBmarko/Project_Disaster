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
console.log(`OK: ${checks} preparedness checks passed. No services, generated results or network used.`)
