import type { FaultFeature, FaultGeometry, GemFaultProperties } from '../types/fault.ts'
import type { Position, ProvinceShape } from './provinceFeatures.ts'

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function line(value: unknown): value is Position[] {
  return Array.isArray(value) && value.length >= 2 && value.every(
    (point: unknown) => Array.isArray(point) && point.length === 2 &&
      point.every((coordinate: unknown) => typeof coordinate === 'number' && Number.isFinite(coordinate)) &&
      Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90,
  ) && value.some((point) => point[0] !== value[0][0] || point[1] !== value[0][1])
}

function geometry(value: unknown): FaultGeometry {
  if (record(value)) {
    if (value.type === 'LineString' && line(value.coordinates)) {
      return { type: 'LineString', coordinates: value.coordinates }
    }
    if (value.type === 'MultiLineString' && Array.isArray(value.coordinates) &&
      value.coordinates.length > 0 && value.coordinates.every(line)) {
      return { type: 'MultiLineString', coordinates: value.coordinates }
    }
  }
  throw new Error('Fault geometry must contain nonempty finite LineString/MultiLineString coordinates')
}

export function faultLines(value: FaultGeometry): readonly (readonly Position[])[] {
  return value.type === 'LineString' ? [value.coordinates] : value.coordinates
}

/** Pure source adapter, shared verbatim by the application and validator. */
export function parseFaultFeatures(value: unknown): FaultFeature[] {
  if (!record(value) || value.type !== 'FeatureCollection' || !Array.isArray(value.features) || !value.features.length) {
    throw new Error('Fault data must be a nonempty GeoJSON FeatureCollection')
  }
  const ids = new Set<string>()
  return value.features.map((feature: unknown) => {
    if (!record(feature) || feature.type !== 'Feature' || !record(feature.properties)) {
      throw new Error('Invalid fault feature/properties')
    }
    const properties: GemFaultProperties = feature.properties
    const sourceId = text(properties.catalog_id)
    if (!sourceId || ids.has(sourceId)) throw new Error('Missing or duplicate fault catalog_id')
    ids.add(sourceId)
    const sourceName = text(properties.name)
    return {
      id: sourceId,
      geometry: geometry(feature.geometry),
      properties: {
        sourceId,
        sourceCatalog: text(properties.catalog_name),
        sourceName,
        displayName: sourceName ?? 'Adsız Fay Segmenti',
      },
    }
  })
}

export type GeographicBounds = { west: number; south: number; east: number; north: number }

/** Derive the geographic window from the existing province asset, never guess it. */
export function provinceBounds(shapes: readonly ProvinceShape[]): GeographicBounds {
  const points = shapes.flatMap((shape) => shape.rings.flat())
  return {
    west: Math.min(...points.map(([x]) => x)),
    east: Math.max(...points.map(([x]) => x)),
    south: Math.min(...points.map(([, y]) => y)),
    north: Math.max(...points.map(([, y]) => y)),
  }
}

/** Whole-feature selection only, not a GIS intersection or city association. */
export function isTurkeyFault(feature: FaultFeature, bounds: GeographicBounds): boolean {
  return feature.properties.sourceCatalog === 'EMME' && /^ME_TR/.test(feature.id) &&
    faultLines(feature.geometry).some((points) => points.some(([x, y]) =>
      x >= bounds.west && x <= bounds.east && y >= bounds.south && y <= bounds.north,
    ))
}
