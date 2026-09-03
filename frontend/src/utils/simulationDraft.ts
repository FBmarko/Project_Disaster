import { SIMULATION_INPUTS } from '../constants/simulation.ts'
import type {
  SimulationAction,
  SimulationDraft,
  SimulationErrors,
  SimulationLocation,
  SimulationRequestDraft,
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
    errors.radiusKm = 'Listeden geçerli bir etki alanı seçin.'
  }
  return errors
}

export function prepareSimulationRequest(draft: SimulationDraft):
  | { ok: true; payload: SimulationRequestDraft }
  | { ok: false; errors: SimulationErrors } {
  const errors = validateSimulationDraft(draft)
  const location = selectedSimulationLocation(draft)
  if (!location || Object.keys(errors).length) return { ok: false, errors }
  // Full precision, no scientific calculations, network calls or persistence.
  return { ok: true, payload: {
    ...location,
    magnitude: draft.magnitude,
    depthKm: draft.depthKm,
    radiusKm: draft.radiusKm,
  } }
}

export function createSimulationSetup(): SimulationSetupState {
  return {
    draft: {
      latitude: null,
      longitude: null,
      magnitude: SIMULATION_INPUTS.magnitude.default,
      depthKm: SIMULATION_INPUTS.depthKm.default,
      radiusKm: SIMULATION_INPUTS.radiusKm.default,
    },
    status: 'editing',
  }
}

/** Local setup lifecycle only; a valid submit never claims a simulation completed. */
export function simulationSetupReducer(state: SimulationSetupState, action: SimulationAction): SimulationSetupState {
  switch (action.type) {
    case 'select-location': {
      const draft = { ...state.draft, ...action.location }
      return selectedSimulationLocation(draft) ? { draft, status: 'editing' } : state
    }
    case 'clear-location':
      return { draft: { ...state.draft, latitude: null, longitude: null }, status: 'editing' }
    case 'set-parameter':
      return { draft: { ...state.draft, [action.field]: action.value }, status: 'editing' }
    case 'submit':
      return { ...state, status: prepareSimulationRequest(state.draft).ok ? 'backend-pending' : 'editing' }
  }
}
