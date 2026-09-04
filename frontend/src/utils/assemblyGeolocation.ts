import type { AssemblyCoordinates, AssemblyLocationStatus } from '../types/assembly.ts'
import { hasValidAssemblyCoordinates } from './assemblyAreas.ts'

type LocationCallbacks = {
  onStatus: (status: AssemblyLocationStatus) => void
  onLocation: (location: AssemblyCoordinates) => void
}

/** Called only by the location button. Cancellation ignores late/duplicate browser callbacks. */
export function requestAssemblyLocation(
  geolocation: Pick<Geolocation, 'getCurrentPosition'> | undefined,
  { onStatus, onLocation }: LocationCallbacks,
): () => void {
  let active = true
  const cancel = () => { active = false }
  if (!geolocation) {
    onStatus('unsupported')
    return cancel
  }
  onStatus('loading')
  try {
    geolocation.getCurrentPosition((position) => {
      if (!active) return
      active = false
      const location = { latitude: position.coords.latitude, longitude: position.coords.longitude }
      if (!hasValidAssemblyCoordinates(location)) { onStatus('unavailable'); return }
      onLocation(location)
      onStatus('success')
    }, (error) => {
      if (!active) return
      active = false
      onStatus(error.code === 1 ? 'denied' : error.code === 3 ? 'timeout' : 'unavailable')
    }, { enableHighAccuracy: false, timeout: 10_000, maximumAge: 0 })
  } catch {
    if (active) onStatus('unavailable')
    active = false
  }
  return cancel
}
