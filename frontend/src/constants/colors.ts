/**
 * AFET360 color palette.
 *
 * Risk-map fills require raw values because they are applied as SVG attributes.
 */

import type { RiskLevel } from '@/types/risk'

/**
 * One colour per risk level. `satisfies` keeps this in step with `RiskLevel`
 * (`src/types/risk.ts`), which stays the single definition of the levels themselves.
 */
export const RISK_COLORS = {
  LOW: '#22C55E',
  MEDIUM: '#F59E0B',
  HIGH: '#EF4444',
} as const satisfies Record<RiskLevel, string>
