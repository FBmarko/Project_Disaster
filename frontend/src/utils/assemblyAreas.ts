import { TURKEY_PROVINCES } from '../constants/provinces.ts'
import { REGION_TEXT_LIMIT } from '../constants/assembly.ts'
import type { AssemblyAreaSearch, AssemblyCoordinates, AssemblyRegionDraft, AssemblyRegionErrors } from '../types/assembly.ts'

export function hasValidAssemblyCoordinates(point: AssemblyCoordinates | null | undefined): point is AssemblyCoordinates {
  return Boolean(point && typeof point.latitude === 'number' && typeof point.longitude === 'number'
    && Number.isFinite(point.latitude) && Number.isFinite(point.longitude)
    && Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180)
}

export function prepareAssemblyRegion(draft: AssemblyRegionDraft):
  | { ok: true; search: Extract<AssemblyAreaSearch, { mode: 'REGION' }> }
  | { ok: false; errors: AssemblyRegionErrors } {
  const errors: AssemblyRegionErrors = {}
  if (!TURKEY_PROVINCES.includes(draft.province)) errors.province = 'Lütfen listeden bir il seçin.'
  for (const field of ['district', 'neighborhood'] as const) {
    if (typeof draft[field] !== 'string' || draft[field].trim().length > REGION_TEXT_LIMIT) {
      errors[field] = `Lütfen en fazla ${REGION_TEXT_LIMIT} karakter girin.`
    }
  }
  if (Object.keys(errors).length) return { ok: false, errors }
  const district = draft.district.trim()
  const neighborhood = draft.neighborhood.trim()
  return { ok: true, search: {
    mode: 'REGION', province: draft.province,
    ...(district ? { district } : {}), ...(neighborhood ? { neighborhood } : {}),
  } }
}

/** Destination only: never add the user's precise origin to a URL. */
export function assemblyDirectionsUrl(point: AssemblyCoordinates | null | undefined): string | null {
  if (!hasValidAssemblyCoordinates(point)) return null
  const params = new URLSearchParams({ api: '1', destination: `${point.latitude},${point.longitude}` })
  return `https://www.google.com/maps/dir/?${params}`
}
