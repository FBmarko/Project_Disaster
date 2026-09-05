export type SimulationLocation = {
  latitude: number
  longitude: number
}

/** Frontend draft only. This is not an agreed backend API contract. */
export type SimulationDraft = {
  latitude: number | null
  longitude: number | null
  magnitude: number
  depthKm: number
  radiusKm: number
}

export type SimulationRequestDraft = SimulationLocation &
  Pick<SimulationDraft, 'magnitude' | 'depthKm' | 'radiusKm'>

export type SimulationParameter = 'magnitude' | 'depthKm' | 'radiusKm'
export type SimulationErrors = Partial<Record<'location' | SimulationParameter, string>>

export type SimulationSetupState = {
  draft: SimulationDraft
  status: 'editing' | 'backend-pending'
}

export type SimulationAction =
  | { type: 'select-location'; location: SimulationLocation }
  | { type: 'clear-location' }
  | { type: 'set-parameter'; field: SimulationParameter; value: number }
  | { type: 'submit' }
