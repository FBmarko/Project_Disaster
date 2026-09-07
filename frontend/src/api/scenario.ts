import { postJson } from './client.ts'
import * as v from './validation.ts'
import type {
  ScenarioPointEstimate,
  ScenarioResult,
  SimulationRequestPayload,
} from '../types/simulation.ts'

export function parsePointEstimate(raw: unknown): ScenarioPointEstimate {
  const r = v.record(raw)
  return {
    surfaceDistanceKm: v.number(r.surface_distance_km),
    rhypoKm: v.number(r.rhypo_km),
    medianPgaG: v.number(r.median_pga_g),
    minus1sigmaPgaG: v.number(r.minus_1sigma_pga_g),
    plus1sigmaPgaG: v.number(r.plus_1sigma_pga_g),
  }
}

export function parseScenarioResponse(raw: unknown): ScenarioResult {
  const root = v.record(raw)
  const m = v.record(root.model)
  const s = v.record(root.scenario)
  const epi = v.record(s.epicenter)
  const scope = v.record(root.model_scope)
  const rawMagGuard = v.array(scope.af360_magnitude_guard).map(v.number)
  const rawVs30Guard = v.array(scope.vs30_m_s).map(v.number)

  const rawMech = v.text(s.mechanism)
  if (rawMech !== 'strike_slip' && rawMech !== 'normal' && rawMech !== 'reverse') {
    return v.invalid()
  }

  const radialProfile = v.array(root.radial_profile).map(parsePointEstimate)
  if (radialProfile.length === 0) {
    return v.invalid()
  }

  return {
    model: {
      name: v.text(m.name),
      citation: v.text(m.citation),
      doi: v.text(m.doi),
      tectonicRegion: v.text(m.tectonic_region),
      component: v.text(m.component),
      intensityMeasure: v.text(m.intensity_measure),
      unit: v.text(m.unit),
    },
    scenario: {
      epicenter: {
        latitude: v.number(epi.latitude),
        longitude: v.number(epi.longitude),
      },
      magnitudeMw: v.number(s.magnitude_mw),
      depthKm: v.number(s.depth_km),
      mechanism: rawMech,
      rakeDegrees: v.number(s.rake_degrees),
      vs30MS: v.number(s.vs30_m_s),
      maxSurfaceDistanceKm: v.number(s.max_surface_distance_km),
    },
    modelScope: {
      af360MagnitudeGuard: [rawMagGuard[0], rawMagGuard[1]],
      maxRhypoKm: v.number(scope.max_rhypo_km),
      maxFocalDepthKm: v.number(scope.max_focal_depth_km),
      vs30MS: [rawVs30Guard[0], rawVs30Guard[1]],
    },
    totalSigmaLn: v.number(root.total_sigma_ln),
    epicenterEstimate: parsePointEstimate(root.epicenter_estimate),
    profileStepKm: v.number(root.profile_step_km),
    radialProfile,
    disclaimer: v.text(root.disclaimer),
  }
}

export async function calculateScenario(
  payload: SimulationRequestPayload,
  signal?: AbortSignal,
): Promise<ScenarioResult> {
  const body = {
    epicenter: {
      latitude: payload.latitude,
      longitude: payload.longitude,
    },
    magnitude_mw: payload.magnitude,
    depth_km: payload.depthKm,
    mechanism: payload.mechanism,
    vs30_m_s: payload.vs30MS,
    max_surface_distance_km: payload.radiusKm,
  }

  return postJson('/api/v1/earthquake-hazards/scenario', body, parseScenarioResponse, signal)
}
