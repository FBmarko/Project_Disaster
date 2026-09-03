import type { FaultFeature } from '@/types/fault'

export type FaultTooltipPlacement = {
  x: number
  y: number
  width: number
  height: number
}

export function FaultTooltip({ feature, selected, placement, id }: {
  feature: FaultFeature
  selected: boolean
  placement: FaultTooltipPlacement
  id: string
}) {
  const width = Math.min(250, Math.max(0, placement.width - 16))
  const left = Math.max(8, Math.min(placement.x + 14, placement.width - width - 8))
  // Fixed maximum height keeps long source names and small screens contained.
  const height = Math.min(116, placement.height - 16)
  const top = Math.max(8, Math.min(placement.y + 14, placement.height - height - 8))
  return (
    <div id={id} role="tooltip" className="pointer-events-none absolute z-10 overflow-hidden rounded-xl border border-border-subtle bg-white p-3 text-sm shadow-lg"
      style={{ left, top, width, maxHeight: height }}>
      <p className="line-clamp-2 font-semibold text-text-primary">{feature.properties.displayName}</p>
      <p className="mt-1 truncate text-xs text-text-secondary">{feature.properties.sourceId}</p>
      <p className="mt-1 text-xs text-brand-red">{selected ? 'Seçili · Detaylar aşağıda' : 'Detaylar için seçin'}</p>
    </div>
  )
}
