import type { FaultMechanism } from '../types/simulation.ts'

/** Scenario input bounds matching Akkar et al. (2014) and AFET360 calibration guards. */
export const SIMULATION_INPUTS = {
  magnitude: { min: 4.0, max: 7.6, step: 0.1, default: 6.5 },
  depthKm: { min: 0.1, max: 30.0, step: 1, default: 10, presets: [5, 10, 20, 30] },
  radiusKm: { options: [25, 50, 100, 150], default: 150 },
} as const

export const FAULT_MECHANISMS: readonly {
  readonly value: FaultMechanism
  readonly label: string
  readonly description: string
}[] = [
  {
    value: 'strike_slip',
    label: 'Doğrultu Atımlı',
    description: 'Yanal ötelenme hareketi (Örn. Kuzey ve Doğu Anadolu Fayları)',
  },
  {
    value: 'normal',
    label: 'Normal',
    description: 'Açılma ve düşey hareket (Örn. Batı Anadolu Grabenleri)',
  },
  {
    value: 'reverse',
    label: 'Ters / Bindirme',
    description: 'Sıkışma ve bindirme kuşağı (Örn. Bitlis-Zagros Bindirme Kuşağı)',
  },
] as const

export const SCENARIO_VS30_ASSUMPTION_MS = 800.0
export const SCENARIO_VS30_LABEL = 'Referans kaya varsayımı · Vs30 = 800 m/s'

export const SIMULATION_MAP = {
  center: { longitude: 35, latitude: 39 },
  zoom: 5,
  // Fit Turkey on first render, including narrow viewports. No location is preselected.
  bounds: [
    [25.5, 35.5],
    [45.0, 42.5],
  ] as [[number, number], [number, number]],
  loadTimeoutMs: 20_000,
} as const
