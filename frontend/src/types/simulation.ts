export type SimulationLocation = {
  latitude: number
  longitude: number
}

export type FaultMechanism = 'strike_slip' | 'normal' | 'reverse'

export type SimulationDraft = {
  latitude: number | null
  longitude: number | null
  magnitude: number
  depthKm: number
  radiusKm: number
  mechanism: FaultMechanism | null
}

export type SimulationRequestPayload = SimulationLocation & {
  magnitude: number
  depthKm: number
  radiusKm: number
  mechanism: FaultMechanism
  vs30MS: number
}

export type SimulationParameter = 'magnitude' | 'depthKm' | 'radiusKm' | 'mechanism'
export type SimulationErrors = Partial<Record<'location' | SimulationParameter, string>>

export type ScenarioPointEstimate = {
  surfaceDistanceKm: number
  rhypoKm: number
  medianPgaG: number
  minus1sigmaPgaG: number
  plus1sigmaPgaG: number
}

export type ScenarioResult = {
  model: {
    name: string
    citation: string
    doi: string
    tectonicRegion: string
    component: string
    intensityMeasure: string
    unit: string
  }
  scenario: {
    epicenter: SimulationLocation
    magnitudeMw: number
    depthKm: number
    mechanism: FaultMechanism
    rakeDegrees: number
    vs30MS: number
    maxSurfaceDistanceKm: number
  }
  modelScope: {
    af360MagnitudeGuard: readonly [number, number]
    maxRhypoKm: number
    maxFocalDepthKm: number
    vs30MS: readonly [number, number]
  }
  totalSigmaLn: number
  epicenterEstimate: ScenarioPointEstimate
  profileStepKm: number
  radialProfile: readonly ScenarioPointEstimate[]
  disclaimer: string
}

export type SimulationSetupState = {
  draft: SimulationDraft
  status: 'editing' | 'loading' | 'success' | 'error'
  result: ScenarioResult | null
  error: string | null
}

export type SimulationAction =
  | { type: 'select-location'; location: SimulationLocation }
  | { type: 'clear-location' }
  | { type: 'set-parameter'; field: 'magnitude' | 'depthKm' | 'radiusKm'; value: number }
  | { type: 'set-mechanism'; mechanism: FaultMechanism }
  | { type: 'submit' }
  | { type: 'start-submit' }
  | { type: 'calculation-success'; result: ScenarioResult }
  | { type: 'calculation-error'; error: string }
