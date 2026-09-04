export interface AssemblyCoordinates {
  latitude: number
  longitude: number
}

export type AssemblyAreaSearch =
  | ({ mode: 'CURRENT_LOCATION' } & AssemblyCoordinates)
  | { mode: 'REGION'; province: string; district?: string; neighborhood?: string }

/** Display model for future approved records, not an invented transport contract. */
export interface AssemblyArea extends AssemblyCoordinates {
  id: string
  name: string
  province: string
  district: string
  neighborhood?: string
  address?: string
}

export interface AssemblyRegionDraft {
  province: string
  district: string
  neighborhood: string
}

export type AssemblyRegionErrors = Partial<Record<keyof AssemblyRegionDraft, string>>

export type AssemblyLocationStatus =
  | 'idle' | 'loading' | 'success' | 'denied' | 'unavailable' | 'timeout' | 'unsupported'
