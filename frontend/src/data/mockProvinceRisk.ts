import { TURKEY_PROVINCES } from '@/constants/provinces'
import type { ProvinceRiskMap, RiskLevel } from '@/types/risk'

/**
 * TEMPORARY placeholder risk data — UI development only.
 *
 * These values are NOT an earthquake risk assessment. They are assigned by a
 * fixed rotation over the official plate-number order of the provinces, purely so
 * that all three legend colours appear on the map and the hover interaction can be
 * exercised. Nothing here is derived from seismic, geological or historical data,
 * and it must never be presented to users as such.
 *
 * The real values will come from the project backend once its API contract exists.
 * Only this file changes at that point: components depend on the `ProvinceRiskMap`
 * shape, not on this constant. See `useProvinceRisk` in
 * `src/hooks/useProvinceRisk.ts` for the seam.
 */

const ROTATION: readonly RiskLevel[] = ['HIGH', 'LOW', 'MEDIUM']

export const mockProvinceRisk: ProvinceRiskMap = Object.freeze(
  Object.fromEntries<RiskLevel>(
    TURKEY_PROVINCES.map((province, index): [string, RiskLevel] => [
      province,
      ROTATION[index % ROTATION.length],
    ]),
  ),
)
