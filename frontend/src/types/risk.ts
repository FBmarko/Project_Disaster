/**
 * Earthquake risk domain types.
 *
 * The three levels are a UI contract: whatever the backend eventually returns is
 * mapped onto exactly these values before it reaches a component.
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

/** Turkish UI labels for each risk level. */
export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  LOW: 'Düşük Risk',
  MEDIUM: 'Orta Risk',
  HIGH: 'Yüksek Risk',
}

/** Legend order — lowest to highest, as in the design reference. */
export const RISK_LEVEL_ORDER: readonly RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH']

/** Risk of a single province, keyed by its canonical Turkish name. */
export type ProvinceRisk = {
  province: string
  level: RiskLevel
}

/**
 * Lookup shape the map consumes. Deliberately minimal so the temporary mock in
 * `src/data/mockProvinceRisk.ts` can be swapped for backend data later without
 * touching any component.
 *
 * A province with no entry is rendered in its neutral state.
 */
export type ProvinceRiskMap = Readonly<Record<string, RiskLevel>>
