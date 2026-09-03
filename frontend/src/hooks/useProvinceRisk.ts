import { mockProvinceRisk } from '@/data/mockProvinceRisk'
import type { ProvinceRiskMap } from '@/types/risk'

/**
 * Single source of province risk for the UI.
 *
 * Today it returns the temporary placeholder dataset synchronously. When the
 * backend contract is defined this hook becomes the only place that changes — it
 * can fetch, cache and expose loading/error state without any map component
 * needing to know, because callers already treat the result as a lookup that may
 * be missing entries.
 */
export function useProvinceRisk(): ProvinceRiskMap {
  return mockProvinceRisk
}
