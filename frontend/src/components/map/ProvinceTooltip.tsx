import { RISK_COLORS } from '@/constants/colors'
import { RISK_LEVEL_LABELS } from '@/types/risk'
import type { RiskLevel } from '@/types/risk'

export type TooltipPlacement = {
  /** Pointer position in pixels, relative to the map container. */
  x: number
  y: number
}

type ProvinceTooltipProps = {
  province: string
  level: RiskLevel | null
  placement: TooltipPlacement
  /** Container size, used to keep the card inside the visible map area. */
  containerWidth: number
  containerHeight: number
}

const TOOLTIP_WIDTH = 190
const OFFSET_X = 14
const OFFSET_Y = 14
const EDGE_PADDING = 8
/** Conservative height estimate; only used to decide whether to flip upwards. */
const ESTIMATED_HEIGHT = 96

/**
 * Floating card describing the hovered province.
 *
 * Positioned absolutely inside the map container and flipped near the right/bottom
 * edges so it never leaves the card. `pointer-events-none` keeps it from stealing
 * hover from the province underneath.
 */
export function ProvinceTooltip({
  province,
  level,
  placement,
  containerWidth,
  containerHeight,
}: ProvinceTooltipProps) {
  const flipX = placement.x + OFFSET_X + TOOLTIP_WIDTH > containerWidth - EDGE_PADDING
  const flipY =
    placement.y + OFFSET_Y + ESTIMATED_HEIGHT > containerHeight - EDGE_PADDING

  const left = flipX
    ? Math.max(EDGE_PADDING, placement.x - OFFSET_X - TOOLTIP_WIDTH)
    : Math.min(placement.x + OFFSET_X, containerWidth - TOOLTIP_WIDTH - EDGE_PADDING)

  const top = flipY
    ? Math.max(EDGE_PADDING, placement.y - OFFSET_Y - ESTIMATED_HEIGHT)
    : placement.y + OFFSET_Y

  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 rounded-xl border border-border-subtle bg-card px-4 py-3 shadow-lg"
      style={{ left, top, width: TOOLTIP_WIDTH }}
    >
      <p className="text-sm font-semibold text-text-primary">{province}</p>

      <p className="mt-1.5 text-xs text-text-secondary">
        Risk Düzeyi:{' '}
        {level ? (
          <span className="font-semibold" style={{ color: RISK_COLORS[level] }}>
            {RISK_LEVEL_LABELS[level]}
          </span>
        ) : (
          <span className="font-semibold text-text-secondary">Veri yok</span>
        )}
      </p>
    </div>
  )
}
