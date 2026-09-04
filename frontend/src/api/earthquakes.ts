import { getJson } from './client.ts'
import * as v from './validation.ts'
import type { FaultEarthquake } from '../types/fault.ts'

export const EARTHQUAKE_LIMIT = 100
export const FAULT_DISTANCE_KM = 25
export function parseFaultEarthquakes(value: unknown, faultId: string) {
  const data = v.collection(value)
  if (v.uuid(data.metadata.fault_id) !== faultId || data.metadata.max_distance_km !== FAULT_DISTANCE_KM) return v.invalid()
  const earthquakes: FaultEarthquake[] = v.uniqueIds(data.features.map(raw => {
    const f = v.record(raw), p = v.record(f.properties), g = v.record(f.geometry)
    const id = v.uuid(f.id), date = v.text(p.occurred_at)
    if (f.type !== 'Feature' || g.type !== 'Point' || v.uuid(p.id) !== id ||
      p.association_method !== 'spatial_proximity' || p.nearest_fault_id !== faultId ||
      !/(Z|[+-]\d{2}:\d{2})$/.test(date) || !Number.isFinite(Date.parse(date))) return v.invalid()
    v.position(g.coordinates)
    return { id, date, location: v.nullableText(p.location_name), magnitude: v.number(p.magnitude),
      magnitudeType: v.text(p.magnitude_type), depthKm: v.nonnegative(p.depth_km),
      distanceKm: v.nonnegative(p.distance_to_fault_km) }
  }))
  v.countMatches(data.metadata.count, earthquakes.length)
  return { earthquakes, attribution: v.text(data.metadata.attribution),
    faultAttribution: v.text(data.metadata.fault_attribution), faultLicense: v.text(data.metadata.fault_license) }
}
export function getFaultEarthquakes(faultId: string, signal: AbortSignal) {
  v.uuid(faultId)
  return getJson(`/api/v1/fault-lines/${encodeURIComponent(faultId)}/earthquakes?max_distance_km=${FAULT_DISTANCE_KM}&min_magnitude=5&limit=${EARTHQUAKE_LIMIT}&order_by=recent`,
    value => parseFaultEarthquakes(value, faultId), signal)
}
