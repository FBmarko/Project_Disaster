/**
 * Seismic hazard domain types and province-level aggregation contracts.
 *
 * All values represent physical ground-motion parameters (PGA in decimal g)
 * derived from the authoritative GEM Global Seismic Hazard Map (GSHM v2026.1).
 * These are hazard parameters on reference rock (Vs30 = 800 m/s), NOT building
 * vulnerability or risk.
 */

export type ProvinceHazardItem = {
  readonly provinceId: string
  readonly plateCode: number
  readonly provinceName: string
  readonly sampleCount: number
  readonly medianPgaG: number | null
  readonly minPgaG: number | null
  readonly maxPgaG: number | null
}

export type ProvinceHazardDataset = {
  readonly source: string
  readonly sourceVersion: string
  readonly modelName: string
  readonly versionDoi: string
  readonly license: string
  readonly attribution: string
}

export type ProvinceHazardMetric = {
  readonly name: string
  readonly unit: string
  readonly returnPeriodYears: number
  readonly exceedanceProbability: number
  readonly timeHorizonYears: number
  readonly referenceVs30Mps: number
  readonly referenceGround: string
}

export type ProvinceHazardCollection = {
  readonly dataset: ProvinceHazardDataset
  readonly metric: ProvinceHazardMetric
  readonly summaryMethod: string
  readonly provinces: readonly ProvinceHazardItem[]
  readonly provincesByName: Readonly<Record<string, ProvinceHazardItem>>
  readonly minMedianPga: number
  readonly maxMedianPga: number
  readonly boundarySource: string
  readonly disclaimer: string
}
