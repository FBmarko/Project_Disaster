import type { ProvinceHazardItem } from '@/types/hazard'

export type TooltipPlacement = {
  /** Pointer position in pixels, relative to the map container. */
  x: number
  y: number
}

type ProvinceTooltipProps = {
  province: string
  hazard: ProvinceHazardItem | null | undefined
  placement: TooltipPlacement
  /** Container size, used to keep the card inside the visible map area. */
  containerWidth: number
  containerHeight: number
}

const TOOLTIP_WIDTH = 220
const OFFSET_X = 14
const OFFSET_Y = 14
const EDGE_PADDING = 8
/** Conservative height estimate; used to decide whether to flip upwards. */
const ESTIMATED_HEIGHT = 130

/**
 * Floating card describing the hovered province's seismic hazard values.
 *
 * Displays numeric median PGA, min-max range, and grid point count with
 * concise reference context (Vs30 = 800 m/s reference rock, 475-year return period).
 */
export function ProvinceTooltip({
  province,
  hazard,
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

      {hazard && hazard.medianPgaG !== null ? (
        <div className="mt-1.5 space-y-1 text-xs text-text-secondary">
          <p className="flex justify-between">
            <span>Medyan PGA:</span>
            <span className="font-semibold text-text-primary">
              {hazard.medianPgaG.toFixed(3)} g
            </span>
          </p>
          {hazard.minPgaG !== null && hazard.maxPgaG !== null ? (
            <p className="flex justify-between">
              <span>PGA Aralığı:</span>
              <span className="font-medium text-text-primary">
                {hazard.minPgaG.toFixed(3)} – {hazard.maxPgaG.toFixed(3)} g
              </span>
            </p>
          ) : null}
          <p className="flex justify-between">
            <span>Grid Noktası:</span>
            <span className="font-medium text-text-primary">{hazard.sampleCount}</span>
          </p>
          <p className="mt-1 border-t border-border-subtle/50 pt-1 text-[10px] text-text-muted">
            475 yıl · Vs30 = 800 m/s referans kaya
          </p>
        </div>
      ) : (
        <p className="mt-1.5 text-xs text-text-muted">PGA verisi bulunamadı</p>
      )}
    </div>
  )
}
