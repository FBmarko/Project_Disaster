import { getJson } from './client.ts'
import * as v from './validation.ts'
import type { ProvinceHazardCollection, ProvinceHazardItem } from '../types/hazard.ts'

/**
 * Validates the raw API response from GET /api/v1/earthquake-hazards/provinces.
 *
 * Enforces all 81 province summaries, unique plate codes and IDs, non-negative
 * sample counts, valid min <= median <= max PGA bounds, and extracts dataset metadata.
 */
export function parseProvinceHazards(value: unknown): ProvinceHazardCollection {
  const root = v.record(value)
  const dsRaw = v.record(root.dataset)
  const metricRaw = v.record(root.metric)
  const provsRaw = v.array(root.provinces)

  if (provsRaw.length !== 81) return v.invalid()

  const dataset = {
    source: v.text(dsRaw.source),
    sourceVersion: v.text(dsRaw.source_version),
    modelName: v.text(dsRaw.model_name),
    versionDoi: v.text(dsRaw.version_doi),
    license: v.text(dsRaw.license),
    attribution: v.text(dsRaw.attribution),
  }

  const metric = {
    name: v.text(metricRaw.name),
    unit: v.text(metricRaw.unit),
    returnPeriodYears: v.nonnegative(metricRaw.return_period_years),
    exceedanceProbability: v.nonnegative(metricRaw.exceedance_probability),
    timeHorizonYears: v.nonnegative(metricRaw.time_horizon_years),
    referenceVs30Mps: v.nonnegative(metricRaw.reference_vs30_mps),
    referenceGround: v.text(metricRaw.reference_ground),
  }

  const summaryMethod = v.text(root.summary_method)
  const boundarySource = v.text(root.boundary_source)
  const disclaimer = v.text(root.disclaimer)

  const seenIds = new Set<string>()
  const seenPlates = new Set<number>()
  const provincesByName: Record<string, ProvinceHazardItem> = {}

  let minMedian = Infinity
  let maxMedian = -Infinity

  const provinces: ProvinceHazardItem[] = provsRaw.map((raw) => {
    const p = v.record(raw)
    const provinceId = v.text(p.province_id)
    const plateCode = v.number(p.plate_code)
    const provinceName = v.text(p.province_name)
    const sampleCount = v.nonnegative(p.sample_count)

    if (seenIds.has(provinceId) || seenPlates.has(plateCode)) {
      return v.invalid()
    }
    seenIds.add(provinceId)
    seenPlates.add(plateCode)

    const minPgaG = p.min_pga_g == null ? null : v.nonnegative(p.min_pga_g)
    const medianPgaG = p.median_pga_g == null ? null : v.nonnegative(p.median_pga_g)
    const maxPgaG = p.max_pga_g == null ? null : v.nonnegative(p.max_pga_g)

    if (medianPgaG !== null) {
      if (minPgaG === null || maxPgaG === null) return v.invalid()
      if (minPgaG > medianPgaG || medianPgaG > maxPgaG) return v.invalid()
      if (medianPgaG < minMedian) minMedian = medianPgaG
      if (medianPgaG > maxMedian) maxMedian = medianPgaG
    }

    const item: ProvinceHazardItem = {
      provinceId,
      plateCode,
      provinceName,
      sampleCount,
      medianPgaG,
      minPgaG,
      maxPgaG,
    }

    provincesByName[provinceName] = item
    return item
  })

  if (minMedian === Infinity) minMedian = 0
  if (maxMedian === -Infinity) maxMedian = 1

  return {
    dataset,
    metric,
    summaryMethod,
    provinces,
    provincesByName,
    minMedianPga: minMedian,
    maxMedianPga: maxMedian,
    boundarySource,
    disclaimer,
  }
}

/**
 * Fetch province seismic hazard summaries from the AFET360 API.
 */
export function getProvinceHazards(signal?: AbortSignal): Promise<ProvinceHazardCollection> {
  return getJson(
    '/api/v1/earthquake-hazards/provinces',
    parseProvinceHazards,
    signal ?? new AbortController().signal,
  )
}
