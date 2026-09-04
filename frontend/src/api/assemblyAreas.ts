import { getJson } from './client.ts'
import * as v from './validation.ts'
import type { AssemblyArea, AssemblyCoordinates, AssemblyGeometry } from '../types/assembly.ts'

export interface BackendAssemblyFeature {
  id: string
  geometry: AssemblyGeometry
  properties: { source_feature_id: string; name: string | null; ref: string | null;
    operator: string | null; distance_km: number }
}
export function mapAssemblyArea(dto: BackendAssemblyFeature): AssemblyArea {
  const p = dto.properties
  return { id: dto.id, name: p.name ?? `Adsız toplanma noktası · ${p.source_feature_id}`,
    sourceId: p.source_feature_id, reference: p.ref, operator: p.operator, distanceKm: p.distance_km,
    geometry: dto.geometry,
    ...(dto.geometry.type === 'Point' ? { longitude: dto.geometry.coordinates[0], latitude: dto.geometry.coordinates[1] } : {}),
  }
}
export function parseAssemblyCollection(value: unknown) {
  const data = v.collection(value)
  if (data.metadata.source !== 'OpenStreetMap' || data.metadata.source_classification !== 'community_open_data') return v.invalid()
  const areas = v.uniqueIds(data.features.map(raw => {
    const f = v.record(raw), p = v.record(f.properties), g = v.record(f.geometry)
    if (f.type !== 'Feature') return v.invalid()
    let geometry: AssemblyGeometry
    if (g.type === 'Point') geometry = { type: 'Point', coordinates: v.position(g.coordinates) }
    else if (g.type === 'Polygon') {
      const coordinates = v.array(g.coordinates).map(rawRing => {
        const ring = v.array(rawRing).map(v.position), end = ring.at(-1)
        if (ring.length < 4 || ring[0][0] !== end?.[0] || ring[0][1] !== end?.[1]) return v.invalid()
        return ring
      })
      if (!coordinates.length) return v.invalid()
      geometry = { type: 'Polygon', coordinates }
    } else return v.invalid()
    return mapAssemblyArea({ id: v.uuid(f.id), geometry, properties: {
      source_feature_id: v.text(p.source_feature_id), name: v.nullableText(p.name),
      ref: v.nullableText(p.ref), operator: v.nullableText(p.operator), distance_km: v.nonnegative(p.distance_km),
    } })
  }))
  v.countMatches(data.metadata.returned_count, areas.length)
  const timestamp = v.text(data.metadata.source_data_timestamp)
  if (!Number.isFinite(Date.parse(timestamp))) return v.invalid()
  return { areas, truncated: v.boolean(data.metadata.truncated), attribution: v.text(data.metadata.attribution),
    license: v.text(data.metadata.license), sourceTimestamp: timestamp }
}
export function getNearbyAssemblyAreas(point: AssemblyCoordinates, radiusKm: number, signal: AbortSignal) {
  v.position([point.longitude, point.latitude])
  if (!(radiusKm > 0 && radiusKm <= 200)) throw new Error('Invalid search radius')
  const query = new URLSearchParams({ lat: String(point.latitude), lon: String(point.longitude), radius_km: String(radiusKm), limit: '100' })
  return getJson(`/api/v1/assembly-areas/nearby?${query}`, parseAssemblyCollection, signal)
}
