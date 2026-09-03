import rawGeoJson from './turkey-provinces.geojson?raw'
import {
  assertFeatureCollection,
  groupFeaturesByProvince,
} from './provinceFeatures.ts'
import type { ProvinceShape } from './provinceFeatures.ts'
import { TURKEY_PROVINCES } from '@/constants/provinces'

/**
 * The bundled Turkey province boundaries, parsed once.
 *
 * The GeoJSON is inlined as a string at build time, so the application never
 * fetches geographic data at runtime. Source and licence:
 * `frontend/docs/data-sources.md`.
 */

export type { Position, Ring, ProvinceShape } from './provinceFeatures.ts'

function parseProvinceShapes(): ProvinceShape[] {
  const parsed: unknown = JSON.parse(rawGeoJson)
  assertFeatureCollection(parsed)
  return groupFeaturesByProvince(parsed.features)
}

export const TURKEY_PROVINCE_SHAPES: readonly ProvinceShape[] = parseProvinceShapes()

/** Provinces in `TURKEY_PROVINCES` that the dataset did not supply. */
export const MISSING_PROVINCES: readonly string[] = TURKEY_PROVINCES.filter(
  (name) => !TURKEY_PROVINCE_SHAPES.some((shape) => shape.name === name),
)
