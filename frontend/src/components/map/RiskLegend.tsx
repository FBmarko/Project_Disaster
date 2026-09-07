import { getHazardGradientCss } from '@/utils/hazardColors'

type RiskLegendProps = {
  readonly minPga?: number | null
  readonly maxPga?: number | null
}

/**
 * Continuous numeric legend displaying the Peak Ground Acceleration (PGA in g) scale.
 *
 * Renders a continuous horizontal color gradient bar between the dataset minimum
 * and maximum median PGA values. Uses neutral numeric descriptors without
 * categorical risk binning or safety labels.
 */
export function RiskLegend({ minPga, maxPga }: RiskLegendProps) {
  const hasRange =
    minPga !== null &&
    minPga !== undefined &&
    maxPga !== null &&
    maxPga !== undefined &&
    Number.isFinite(minPga) &&
    Number.isFinite(maxPga)

  const minLabel = hasRange ? `${minPga.toFixed(3)} g` : '— g'
  const maxLabel = hasRange ? `${maxPga.toFixed(3)} g` : '— g'

  return (
    <div className="rounded-2xl border border-border-subtle/70 bg-surface/60 p-4 sm:p-5">
      <div className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-text-primary">
            Deprem Tehlikesi — Medyan PGA
          </span>
          <span className="text-xs text-text-muted">
            475 yıllık dönüş periyodu (Vs30 = 800 m/s)
          </span>
        </div>

        {/* Continuous gradient spectrum bar */}
        <div
          aria-hidden="true"
          className="h-3.5 w-full rounded-full border border-border-subtle/40 shadow-inner"
          style={{ background: getHazardGradientCss() }}
        />

        {/* Numeric endpoints */}
        <div className="flex items-center justify-between text-xs text-text-secondary">
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Daha düşük PGA:</span>
            <span className="font-semibold text-text-primary">{minLabel}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Daha yüksek PGA:</span>
            <span className="font-semibold text-text-primary">{maxLabel}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export const HazardLegend = RiskLegend
