import type { Position } from '../data/provinceFeatures.ts'

export type FaultGeometry =
  | { type: 'LineString'; coordinates: readonly Position[] }
  | { type: 'MultiLineString'; coordinates: readonly (readonly Position[])[] }

/** External values remain unknown until the source adapter validates them. */
export type GemFaultProperties = {
  catalog_id?: unknown
  catalog_name?: unknown
  name?: unknown
}

export type FaultProperties = {
  sourceId: string
  sourceCatalog: string | null
  sourceName: string | null
  displayName: string
}

export type FaultFeature = {
  id: string
  geometry: FaultGeometry
  properties: FaultProperties
}

export type FaultEarthquake = {
  id: string
  date: string
  location: string
  magnitude: number
}

/** Supplied data only: these components never infer city or earthquake links. */
export type FaultLineDetail = {
  faultId: string
  status: 'backend-pending' | 'development' | 'ready'
  cities: readonly string[]
  earthquakes: readonly FaultEarthquake[]
}
