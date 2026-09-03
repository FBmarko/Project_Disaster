import raw from './turkey-active-faults.geojson?raw'
import { parseFaultFeatures } from './faultFeatures.ts'
import type { FaultFeature } from '../types/fault.ts'

/** Static build-time asset: no network request, API key, or third-party runtime. */
export function loadTurkeyFaults():
  | { status: 'ready'; features: readonly FaultFeature[] }
  | { status: 'error'; features: readonly FaultFeature[] } {
  try {
    const parsed: unknown = JSON.parse(raw)
    return { status: 'ready', features: parseFaultFeatures(parsed) }
  } catch {
    return { status: 'error', features: [] }
  }
}
