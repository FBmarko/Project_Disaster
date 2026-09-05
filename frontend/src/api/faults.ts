import { getJson } from './client.ts'
import * as v from './validation.ts'
import type { FaultFeature, FaultGeometry } from '../types/fault.ts'

/** Consumed fields from FaultFeatureProperties, kept separate from the UI model. */
export interface BackendFault {
  id: string
  geometry: Extract<FaultGeometry, { type: 'MultiLineString' }>
  properties: { id: string; source: string; source_feature_id: string; name: string | null;
    segment_name: string | null; fault_type: string | null; activity_status: string | null }
}
export function mapFault(dto: BackendFault): FaultFeature {
  return { id: dto.id, geometry: dto.geometry, properties: {
    sourceId: dto.properties.source_feature_id, sourceCatalog: dto.properties.source,
    sourceName: dto.properties.name,
    displayName: dto.properties.segment_name ?? dto.properties.name ?? 'Adsız Fay Segmenti',
    faultType: dto.properties.fault_type, activityStatus: dto.properties.activity_status,
  } }
}
export function parseFaultCollection(value: unknown) {
  const data = v.collection(value)
  const features = v.uniqueIds(data.features.map(raw => {
    const feature = v.record(raw), p = v.record(feature.properties), g = v.record(feature.geometry)
    const id = v.uuid(feature.id)
    if (feature.type !== 'Feature' || g.type !== 'MultiLineString' || v.uuid(p.id) !== id) return v.invalid()
    const coordinates = v.array(g.coordinates).map(rawLine => {
      const line = v.array(rawLine).map(v.position)
      if (line.length < 2 || !line.some(point => point[0] !== line[0][0] || point[1] !== line[0][1])) return v.invalid()
      return line
    })
    if (!coordinates.length || p.source !== 'GEM_GAF') return v.invalid()
    return mapFault({ id, geometry: { type: 'MultiLineString', coordinates }, properties: {
      id, source: p.source, source_feature_id: v.text(p.source_feature_id),
      name: v.nullableText(p.name), segment_name: v.nullableText(p.segment_name),
      fault_type: v.nullableText(p.fault_type), activity_status: v.nullableText(p.activity_status),
    } })
  }))
  v.countMatches(data.metadata.count, features.length)
  return { features, attribution: v.text(data.metadata.attribution), license: v.text(data.metadata.license) }
}

export const FAULT_LIMIT = 2000
export function getFaults(signal: AbortSignal) {
  // Documented Türkiye tectonic context; source coordinates are never clipped or joined to local IDs.
  return getJson(`/api/v1/fault-lines?bbox=24,34,46,44&limit=${FAULT_LIMIT}`, parseFaultCollection, signal)
}
