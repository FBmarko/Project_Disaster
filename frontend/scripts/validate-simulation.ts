/** Offline checks of the exact validation and state transitions used by /simulation. */
import assert from 'node:assert/strict'
import { SCENARIO_VS30_ASSUMPTION_MS, SIMULATION_INPUTS } from '../src/constants/simulation.ts'
import {
  createSimulationSetup,
  prepareSimulationRequest,
  selectedSimulationLocation,
  simulationSetupReducer,
  validateSimulationDraft,
} from '../src/utils/simulationDraft.ts'
import type { FaultMechanism, ScenarioResult, SimulationDraft, SimulationParameter } from '../src/types/simulation.ts'

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

check('No preselected location or valid submission without mandatory inputs', () => {
  assert.equal(selectedSimulationLocation(initial.draft), null)
  assert.equal(initial.draft.mechanism, null)
  assert.equal(prepareSimulationRequest(initial.draft).ok, false)
  assert.equal(simulationSetupReducer(initial, { type: 'submit' }).status, 'editing')
})

check('Fault mechanism is mandatory; missing mechanism prevents submission', () => {
  assert.equal(selected.draft.mechanism, null)
  const errors = validateSimulationDraft(selected.draft)
  assert(errors.mechanism)
  assert.equal(prepareSimulationRequest(selected.draft).ok, false)
})

const configured = simulationSetupReducer(selected, { type: 'set-mechanism', mechanism: 'strike_slip' })

check('Complete payload keeps exact coordinate precision and scientific defaults', () => {
  const result = prepareSimulationRequest(configured.draft)
  assert.equal(result.ok, true)
  if (result.ok) {
    assert.deepEqual(result.payload, {
      ...location,
      magnitude: 6.5,
      depthKm: 10,
      radiusKm: 150,
      mechanism: 'strike_slip',
      vs30MS: SCENARIO_VS30_ASSUMPTION_MS,
    })
  }
})

check('Each coordinate must exist and be finite/in geographic range', () => {
  for (const [key, invalid] of [
    ['latitude', null], ['longitude', null], ['latitude', NaN], ['longitude', Infinity],
    ['latitude', 91], ['latitude', -91], ['longitude', 181], ['longitude', -181],
  ] as const) {
    const draft = { ...configured.draft, [key]: invalid }
    assert(validateSimulationDraft(draft).location)
    assert.equal(prepareSimulationRequest(draft).ok, false)
  }
  assert.equal(prepareSimulationRequest({ ...configured.draft, latitude: 0, longitude: 0 }).ok, true)
})

check('Magnitude and depth boundary values accepted; out-of-range/nonfinite values rejected', () => {
  for (const field of ['magnitude', 'depthKm'] as const) {
    const { min, max } = SIMULATION_INPUTS[field]
    for (const value of [min, max]) assert.equal(prepareSimulationRequest({ ...configured.draft, [field]: value }).ok, true)
    for (const value of [min - 0.1, max + 0.1, NaN, Infinity, -Infinity]) {
      assert(validateSimulationDraft({ ...configured.draft, [field]: value })[field])
      assert.equal(prepareSimulationRequest({ ...configured.draft, [field]: value }).ok, false)
    }
  }
})

check('Only configured calculation radii are valid', () => {
  for (const radiusKm of SIMULATION_INPUTS.radiusKm.options) {
    assert.equal(prepareSimulationRequest({ ...configured.draft, radiusKm }).ok, true)
  }
  for (const radiusKm of [0, 75, 151, NaN, Infinity]) {
    assert(validateSimulationDraft({ ...configured.draft, radiusKm }).radiusKm)
  }
})

check('All valid fault mechanisms accepted; invalid rejected', () => {
  for (const mech of ['strike_slip', 'normal', 'reverse'] as const) {
    assert.equal(prepareSimulationRequest({ ...configured.draft, mechanism: mech }).ok, true)
  }
  for (const mech of ['oblique', 'unknown', '', null] as unknown as FaultMechanism[]) {
    assert(validateSimulationDraft({ ...configured.draft, mechanism: mech }).mechanism)
    assert.equal(prepareSimulationRequest({ ...configured.draft, mechanism: mech }).ok, false)
  }
})

check('Valid start produces loading state; calculation success sets result; calculation error sets error', () => {
  const submitted = simulationSetupReducer(configured, { type: 'start-submit' })
  assert.equal(submitted.status, 'loading')
  assert.equal(submitted.error, null)

  const mockResult = {
    model: {
      name: 'Akkar et al. (2014) Rhyp Point-Source GMPE',
      citation: 'Akkar et al. (2014)',
      doi: '10.1007/s10518-013-9461-4',
      tectonicRegion: 'active_shallow_crust',
      component: 'geometric_mean_horizontal',
      intensityMeasure: 'PGA',
      unit: 'g',
    },
    scenario: {
      epicenter: location,
      magnitudeMw: 6.5,
      depthKm: 10,
      mechanism: 'strike_slip' as const,
      rakeDegrees: 0,
      vs30MS: 800,
      maxSurfaceDistanceKm: 150,
    },
    modelScope: {
      af360MagnitudeGuard: [4.0, 7.6] as const,
      maxRhypoKm: 200,
      maxFocalDepthKm: 30,
      vs30MS: [150, 1200] as const,
    },
    totalSigmaLn: 0.7347,
    epicenterEstimate: {
      surfaceDistanceKm: 0,
      rhypoKm: 10,
      medianPgaG: 0.4273,
      minus1sigmaPgaG: 0.2049,
      plus1sigmaPgaG: 0.8911,
    },
    profileStepKm: 5,
    radialProfile: [],
    disclaimer: 'Bilimsel uyari',
  } as unknown as ScenarioResult

  const succeeded = simulationSetupReducer(submitted, { type: 'calculation-success', result: mockResult })
  assert.equal(succeeded.status, 'success')
  assert.equal(succeeded.result, mockResult)
  assert.equal(succeeded.error, null)

  const errored = simulationSetupReducer(submitted, { type: 'calculation-error', error: 'Network error' })
  assert.equal(errored.status, 'error')
  assert.equal(errored.error, 'Network error')
})

check('Replacing the epicenter replaces coordinate pair and resets state to editing', () => {
  const replacement = { latitude: 39.123456789, longitude: 35.987654321 }
  const updated = simulationSetupReducer(configured, { type: 'select-location', location: replacement })
  assert.deepEqual(selectedSimulationLocation(updated.draft), replacement)
  assert.equal(updated.status, 'editing')
  assert.deepEqual(selectedSimulationLocation(configured.draft), location)
})

check('Clearing removes both coordinates and invalidates submission while preserving settings', () => {
  const cleared = simulationSetupReducer(configured, { type: 'clear-location' })
  assert.equal(selectedSimulationLocation(cleared.draft), null)
  assert.equal(cleared.status, 'editing')
  assert.equal(prepareSimulationRequest(cleared.draft).ok, false)
  assert.equal(cleared.draft.magnitude, configured.draft.magnitude)
  assert.equal(cleared.draft.mechanism, 'strike_slip')
})

check('Changing each control resets feedback; invalid values cannot be submitted', () => {
  for (const [field, value] of [['magnitude', 7.2], ['depthKm', 30], ['radiusKm', 100]] as [SimulationParameter, number][]) {
    const updated = simulationSetupReducer(configured, { type: 'set-parameter', field, value })
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
  const malformed = { ...configured.draft, latitude: '40.8', magnitude: '7.2' } as unknown as SimulationDraft
  assert.equal(prepareSimulationRequest(malformed).ok, false)
  assert(validateSimulationDraft(malformed).magnitude)
})

console.log(`OK: ${checks} simulation setup checks passed. No Google key, API, results or network used.`)
