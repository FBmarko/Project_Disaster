/**
 * AFET360 color palette.
 *
 * Tailwind utilities are the primary way to style components (see
 * `src/index.css`). These constants exist for cases where a raw color value is
 * needed in TypeScript — map layers, canvas/SVG fills, chart libraries.
 */

import type { RiskLevel } from '@/types/risk'

export const COLORS = {
  brandRed: '#EF2B2D',
  brandRedSoft: 'rgba(239, 43, 45, 0.08)',
  surface: '#F8FAFC',
  card: '#FFFFFF',
  textPrimary: '#111827',
  textSecondary: '#6B7280',
  border: '#E5E7EB',
} as const

/**
 * One colour per risk level. `satisfies` keeps this in step with `RiskLevel`
 * (`src/types/risk.ts`), which stays the single definition of the levels themselves.
 */
export const RISK_COLORS = {
  LOW: '#22C55E',
  MEDIUM: '#F59E0B',
  HIGH: '#EF4444',
} as const satisfies Record<RiskLevel, string>
