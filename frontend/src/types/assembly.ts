export interface AssemblyCoordinates {
  latitude: number
  longitude: number
}

export type AssemblyAreaSearch =
  | ({ mode: 'CURRENT_LOCATION' } & AssemblyCoordinates)
  | { mode: 'REGION'; province: string; district?: string; neighborhood?: string }

/** Native geometry from the public assembly API; no generated destination points. */
export type AssemblyGeometry =
  | { type: 'Point'; coordinates: readonly [number, number] }
  | { type: 'Polygon'; coordinates: readonly (readonly (readonly [number, number])[])[] }

export interface AssemblyArea {
  id: string
  name: string
  latitude?: number
  longitude?: number
  province?: string
  district?: string
  neighborhood?: string
  address?: string
  geometry?: AssemblyGeometry
  sourceId?: string
  reference?: string | null
  operator?: string | null
  distanceKm?: number
}

export interface AssemblyRegionDraft {
  province: string
  district: string
  neighborhood: string
}

export type AssemblyRegionErrors = Partial<Record<keyof AssemblyRegionDraft, string>>

export type AssemblyLocationStatus =
  | 'idle' | 'loading' | 'success' | 'denied' | 'unavailable' | 'timeout' | 'unsupported'
