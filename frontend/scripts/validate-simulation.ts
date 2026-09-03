/** Offline checks of the exact validation and state transitions used by /simulation. */
import assert from 'node:assert/strict'
import { SIMULATION_INPUTS } from '../src/constants/simulation.ts'
import { createSimulationSetup, prepareSimulationRequest, selectedSimulationLocation, simulationSetupReducer, validateSimulationDraft } from '../src/utils/simulationDraft.ts'
import type { SimulationDraft, SimulationParameter } from '../src/types/simulation.ts'

let checks = 0
function check(name: string, run: () => void) {
  run()
  checks += 1
  console.log(`PASS: ${name}`)
}

const initial = createSimulationSetup()
// User-request example, only a form input; never a simulated result or a map substitute.
const location = { latitude: 40.81234567890123, longitude: 29.42312345678901 }
const selected = simulationSetupReducer(initial, { type: 'select-location', location })

check('No preselected location or valid submission', () => {
  assert.equal(selectedSimulationLocation(initial.draft), null)
  assert.equal(prepareSimulationRequest(initial.draft).ok, false)
  assert.equal(simulationSetupReducer(initial, { type: 'submit' }).status, 'editing')
})
check('Complete payload keeps exact coordinate precision', () => {
  const result = prepareSimulationRequest(selected.draft)
  assert.equal(result.ok, true)
  if (result.ok) assert.deepEqual(result.payload, { ...location, magnitude: 6, depthKm: 20, radiusKm: 50 })
})
check('Each coordinate must exist and be finite/in geographic range', () => {
  for (const [key, invalid] of [
    ['latitude', null], ['longitude', null], ['latitude', NaN], ['longitude', Infinity],
    ['latitude', 91], ['latitude', -91], ['longitude', 181], ['longitude', -181],
  ] as const) {
    const draft = { ...selected.draft, [key]: invalid }
    assert(validateSimulationDraft(draft).location)
    assert.equal(prepareSimulationRequest(draft).ok, false)
  }
  assert.equal(prepareSimulationRequest({ ...selected.draft, latitude: 0, longitude: 0 }).ok, true)
})
check('Magnitude and depth boundary values accepted; out-of-range/nonfinite values rejected', () => {
  for (const field of ['magnitude', 'depthKm'] as const) {
    const { min, max } = SIMULATION_INPUTS[field]
    for (const value of [min, max]) assert.equal(prepareSimulationRequest({ ...selected.draft, [field]: value }).ok, true)
    for (const value of [min - 0.1, max + 0.1, NaN, Infinity, -Infinity]) {
      assert(validateSimulationDraft({ ...selected.draft, [field]: value })[field])
      assert.equal(prepareSimulationRequest({ ...selected.draft, [field]: value }).ok, false)
    }
  }
})
check('Only configured impact radii are valid', () => {
  for (const radiusKm of SIMULATION_INPUTS.radiusKm.options) assert.equal(prepareSimulationRequest({ ...selected.draft, radiusKm }).ok, true)
  for (const radiusKm of [0, 75, 151, NaN, Infinity]) assert(validateSimulationDraft({ ...selected.draft, radiusKm }).radiusKm)
})
check('Valid start produces only a backend-pending state', () => {
  const submitted = simulationSetupReducer(selected, { type: 'submit' })
  assert.deepEqual(submitted, { draft: selected.draft, status: 'backend-pending' })
  assert.equal(simulationSetupReducer(submitted, { type: 'submit' }).status, 'backend-pending')
})
check('Replacing the epicenter replaces one coordinate pair and clears stale feedback', () => {
  const submitted = simulationSetupReducer(selected, { type: 'submit' })
  const replacement = { latitude: 39.123456789, longitude: 35.987654321 }
  const updated = simulationSetupReducer(submitted, { type: 'select-location', location: replacement })
  assert.deepEqual(selectedSimulationLocation(updated.draft), replacement)
  assert.equal(updated.status, 'editing')
  assert.deepEqual(selectedSimulationLocation(selected.draft), location)
})
check('Clearing removes both coordinates and invalidates submission while preserving settings', () => {
  const cleared = simulationSetupReducer(simulationSetupReducer(selected, { type: 'submit' }), { type: 'clear-location' })
  assert.equal(selectedSimulationLocation(cleared.draft), null)
  assert.equal(cleared.status, 'editing')
  assert.equal(prepareSimulationRequest(cleared.draft).ok, false)
  assert.equal(cleared.draft.magnitude, selected.draft.magnitude)
})
check('Changing each control resets feedback; invalid values cannot be submitted', () => {
  const submitted = simulationSetupReducer(selected, { type: 'submit' })
  for (const [field, value] of [['magnitude', 7.2], ['depthKm', 30], ['radiusKm', 150]] as [SimulationParameter, number][]) {
    const updated = simulationSetupReducer(submitted, { type: 'set-parameter', field, value })
    assert.equal(updated.draft[field], value)
    assert.equal(updated.status, 'editing')
    const invalid = simulationSetupReducer(updated, { type: 'set-parameter', field, value: NaN })
    assert.equal(simulationSetupReducer(invalid, { type: 'submit' }).status, 'editing')
  }
})
check('Malformed map coordinate callbacks do not destroy a previous valid selection', () => {
  assert.equal(simulationSetupReducer(selected, { type: 'select-location', location: { latitude: NaN, longitude: 35 } }), selected)
})
check('Validation rejects unexpected runtime types, not just invalid HTML input', () => {
  const malformed = { ...selected.draft, latitude: '40.8', magnitude: '7.2' } as unknown as SimulationDraft
  assert.equal(prepareSimulationRequest(malformed).ok, false)
  assert(validateSimulationDraft(malformed).magnitude)
})
console.log(`OK: ${checks} simulation setup checks passed. No Google key, API, results or network used.`)
