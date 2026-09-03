import { TURKEY_PROVINCES, resolveProvinceName } from '../constants/provinces.ts'

/**
 * GeoJSON reading helpers for the province dataset.
 *
 * Kept free of any bundler-specific import (no `?raw`, no `@/` alias) so that both
 * the application and the `scripts/validate-provinces.ts` checker can share exactly
 * one implementation of "which property holds the province name" and "how features
 * are grouped into provinces". Explicit `.ts` extensions are required for Node to
 * run this module directly.
 */

/** `[longitude, latitude]` */
export type Position = readonly [number, number]

/** A closed linear ring. Interior rings (lakes) are kept and drawn even-odd. */
export type Ring = readonly Position[]

export type ProvinceShape = {
  /** Canonical Turkish province name. */
  name: string
  /** Every ring of the province, whether it came from a Polygon or MultiPolygon. */
  rings: readonly Ring[]
}

export type GeoJsonGeometry = {
  type: string
  coordinates?: unknown
}

export type GeoJsonFeature = {
  type?: string
  properties?: Record<string, unknown> | null
  geometry?: GeoJsonGeometry | null
}

export type GeoJsonFeatureCollection = {
  type?: string
  features?: GeoJsonFeature[]
}

/**
 * Property keys that public Turkey datasets use for the province name, in the order
 * they are tried. Extending this list is preferable to reshaping the raw data.
 */
export const NAME_PROPERTY_KEYS: readonly string[] = [
  'name',
  'Name',
  'NAME',
  'name_tr',
  'NAME_1',
  'shapeName',
  'province',
  'il',
  'il_adi',
  'ADM1_TR',
  'ADMIN',
]

/** First non-empty string among the known name properties. */
export function readProvinceNameProperty(
  properties: Record<string, unknown> | null | undefined,
): string | null {
  if (!properties) return null

  for (const key of NAME_PROPERTY_KEYS) {
    const value = properties[key]
    if (typeof value === 'string' && value.trim() !== '') return value
  }

  return null
}

/** Flattens Polygon / MultiPolygon coordinates to a flat list of rings. */
export function extractRings(geometry: GeoJsonGeometry | null | undefined): Ring[] {
  if (!geometry) return []

  if (geometry.type === 'Polygon') {
    return (geometry.coordinates as Position[][] | undefined) ?? []
  }

  if (geometry.type === 'MultiPolygon') {
    return ((geometry.coordinates as Position[][][] | undefined) ?? []).flat()
  }

  return []
}

export function assertFeatureCollection(
  value: unknown,
): asserts value is GeoJsonFeatureCollection & { features: GeoJsonFeature[] } {
  const candidate = value as GeoJsonFeatureCollection | null

  if (
    !candidate ||
    candidate.type !== 'FeatureCollection' ||
    !Array.isArray(candidate.features)
  ) {
    throw new Error('Province data is not a GeoJSON FeatureCollection')
  }
}

/**
 * Groups features into one shape per canonical province.
 *
 * Features whose name cannot be resolved to a Turkish province, or that carry no
 * usable geometry, are skipped rather than guessed at. A province split across
 * several features is merged, so it stays a single hoverable unit. Output follows
 * official plate-number order for predictable DOM/tab order.
 */
export function groupFeaturesByProvince(
  features: readonly GeoJsonFeature[],
): ProvinceShape[] {
  const ringsByProvince = new Map<string, Ring[]>()

  for (const feature of features) {
    const rawName = readProvinceNameProperty(feature.properties)
    if (rawName === null) continue

    const name = resolveProvinceName(rawName)
    if (name === null) continue

    // A ring needs at least 3 distinct vertices plus the closing point.
    const rings = extractRings(feature.geometry).filter((ring) => ring.length >= 4)
    if (rings.length === 0) continue

    const existing = ringsByProvince.get(name)
    if (existing) existing.push(...rings)
    else ringsByProvince.set(name, [...rings])
  }

  return TURKEY_PROVINCES.filter((name) => ringsByProvince.has(name)).map((name) => ({
    name,
    rings: ringsByProvince.get(name) as Ring[],
  }))
}
