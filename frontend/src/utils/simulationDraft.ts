import { SCENARIO_VS30_ASSUMPTION_MS, SIMULATION_INPUTS } from '../constants/simulation.ts'
import type {
  SimulationAction,
  SimulationDraft,
  SimulationErrors,
  SimulationLocation,
  SimulationRequestPayload,
  SimulationSetupState,
} from '../types/simulation.ts'

function inRange(value: number | null, min: number, max: number): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max
}

export function selectedSimulationLocation(draft: SimulationDraft): SimulationLocation | null {
  return inRange(draft.latitude, -90, 90) && inRange(draft.longitude, -180, 180)
    ? { latitude: draft.latitude, longitude: draft.longitude }
    : null
}

export function validateSimulationDraft(draft: SimulationDraft): SimulationErrors {
  const errors: SimulationErrors = {}
  const { magnitude, depthKm, radiusKm } = SIMULATION_INPUTS
  if (!selectedSimulationLocation(draft)) errors.location = 'Harita üzerinden geçerli bir konum seçin.'
  if (!inRange(draft.magnitude, magnitude.min, magnitude.max)) {
    errors.magnitude = `Deprem büyüklüğü ${magnitude.min.toFixed(1)}–${magnitude.max.toFixed(1)} Mw aralığında olmalıdır.`
  }
  if (!inRange(draft.depthKm, depthKm.min, depthKm.max)) {
    errors.depthKm = `Derinlik ${depthKm.min}–${depthKm.max} km aralığında olmalıdır.`
  }
  if (!radiusKm.options.some((value) => value === draft.radiusKm)) {
    errors.radiusKm = 'Listeden geçerli bir hesaplama yarıçapı seçin.'
  }
  if (!draft.mechanism || !['strike_slip', 'normal', 'reverse'].includes(draft.mechanism)) {
    errors.mechanism = 'Lütfen geçerli bir fay mekanizması seçin.'
  }
  return errors
}

export function prepareSimulationRequest(draft: SimulationDraft):
  | { ok: true; payload: SimulationRequestPayload }
  | { ok: false; errors: SimulationErrors } {
  const errors = validateSimulationDraft(draft)
  const location = selectedSimulationLocation(draft)
  if (!location || !draft.mechanism || Object.keys(errors).length > 0) return { ok: false, errors }
  return {
    ok: true,
    payload: {
      ...location,
      magnitude: draft.magnitude,
      depthKm: draft.depthKm,
      radiusKm: draft.radiusKm,
      mechanism: draft.mechanism,
      vs30MS: SCENARIO_VS30_ASSUMPTION_MS,
    },
  }
}

export function createSimulationSetup(): SimulationSetupState {
  return {
    draft: {
      latitude: null,
      longitude: null,
      magnitude: SIMULATION_INPUTS.magnitude.default,
      depthKm: SIMULATION_INPUTS.depthKm.default,
      radiusKm: SIMULATION_INPUTS.radiusKm.default,
      mechanism: null,
    },
    status: 'editing',
    result: null,
    error: null,
  }
}

/** Local setup lifecycle and scenario calculation status management. */
export function simulationSetupReducer(state: SimulationSetupState, action: SimulationAction): SimulationSetupState {
  switch (action.type) {
    case 'select-location': {
      const draft = { ...state.draft, ...action.location }
      return selectedSimulationLocation(draft)
        ? { ...state, draft, status: 'editing', error: null }
        : state
    }
    case 'clear-location':
      return {
        ...state,
        draft: { ...state.draft, latitude: null, longitude: null },
        status: 'editing',
        error: null,
      }
    case 'set-parameter':
      return {
        ...state,
        draft: { ...state.draft, [action.field]: action.value },
        status: 'editing',
        error: null,
      }
    case 'set-mechanism':
      return {
        ...state,
        draft: { ...state.draft, mechanism: action.mechanism },
        status: 'editing',
        error: null,
      }
    case 'submit':
    case 'start-submit':
      return {
        ...state,
        status: prepareSimulationRequest(state.draft).ok ? 'loading' : 'editing',
        error: null,
      }
    case 'calculation-success':
      return {
        ...state,
        status: 'success',
        result: action.result,
        error: null,
      }
    case 'calculation-error':
      return {
        ...state,
        status: 'error',
        error: action.error,
      }
  }
}
