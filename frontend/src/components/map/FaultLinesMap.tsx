import { useId, useMemo, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { TURKEY_MAP } from './turkeyMapGeometry'
import { projectFaultLines } from './projectFaultLines'
import type { FaultPath } from './projectFaultLines'
import { FaultTooltip } from './FaultTooltip'
import type { FaultTooltipPlacement } from './FaultTooltip'
import type { FaultFeature } from '@/types/fault'

export function FaultLinesMap({ features, selectedId, onSelect }: {
  features: readonly FaultFeature[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const tooltipId = useId()
  const helpId = useId()
  const paths = useMemo(() => projectFaultLines(features, TURKEY_MAP), [features])
  const [active, setActive] = useState<{ path: FaultPath; placement: FaultTooltipPlacement } | null>(null)
  const selected = paths.find((path) => path.feature.id === selectedId)

  function activate(path: FaultPath, event?: PointerEvent<SVGPathElement>) {
    const rect = container.current?.getBoundingClientRect()
    if (!rect) return
    setActive({ path, placement: {
      x: event ? event.clientX - rect.left : path.anchor.x * rect.width / TURKEY_MAP.width,
      y: event ? event.clientY - rect.top : path.anchor.y * rect.width / TURKEY_MAP.width,
      width: rect.width,
      height: rect.height,
    } })
  }

  const pointerHandlers = (path: FaultPath) => ({
    onPointerEnter: (event: PointerEvent<SVGPathElement>) => activate(path, event),
    onPointerMove: (event: PointerEvent<SVGPathElement>) => activate(path, event),
    onPointerLeave: () => setActive(null),
    onClick: () => onSelect(path.feature.id),
  })

  return (
    <div ref={container} className="relative w-full" onPointerLeave={() => setActive(null)}>
      <p id={helpId} className="sr-only">Fay segmentlerini Tab ile gezin; Enter veya Boşluk ile seçin. İsterseniz haritanın altındaki seçim listesini kullanın.</p>
      <svg viewBox={TURKEY_MAP.viewBox} className="block h-auto w-full overflow-hidden"
        role="group" aria-label="Türkiye aktif fay haritası" aria-describedby={helpId}>
        <g aria-hidden="true" fill="#FFFFFF" stroke="#9CA3AF" strokeWidth={0.8}>
          {TURKEY_MAP.provinces.map((province) => <path key={province.name} d={province.d}
            fillRule="evenodd" vectorEffect="non-scaling-stroke" />)}
        </g>
        {/* Wide hit targets below the visible strokes: exact line hits take priority. */}
        <g fill="none" stroke="transparent" strokeWidth={12} strokeLinecap="round">
          {paths.map((path) => <path key={path.feature.id} d={path.d}
            vectorEffect="non-scaling-stroke" className="cursor-pointer"
            role="button" tabIndex={0} aria-pressed={selectedId === path.feature.id}
            aria-label={`${path.feature.properties.displayName} · ${path.feature.id}`}
            aria-describedby={active?.path.feature.id === path.feature.id ? tooltipId : undefined}
            {...pointerHandlers(path)} onFocus={() => activate(path)} onBlur={() => setActive(null)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(path.feature.id) }
              if (event.key === 'Escape') setActive(null)
            }} />)}
        </g>
        <g aria-hidden="true" fill="none" stroke="#EF2B2D" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
          {paths.map((path) => <path key={path.feature.id} d={path.d}
            vectorEffect="non-scaling-stroke" className="cursor-pointer" {...pointerHandlers(path)} />)}
        </g>
        {/* Persistent selection has a white casing and a substantially thicker red stroke. */}
        <g aria-hidden="true" pointerEvents="none" fill="none" strokeLinecap="round" strokeLinejoin="round">
          {selected ? <>
            <path d={selected.d} stroke="white" strokeWidth={6} vectorEffect="non-scaling-stroke" />
            <path d={selected.d} stroke="#B91C1C" strokeWidth={3.5} vectorEffect="non-scaling-stroke" />
          </> : null}
          {active && active.path.feature.id !== selectedId ? <path d={active.path.d} stroke="#B91C1C" strokeWidth={2.8} vectorEffect="non-scaling-stroke" /> : null}
        </g>
      </svg>
      {active ? <FaultTooltip id={tooltipId} feature={active.path.feature}
        selected={active.path.feature.id === selectedId} placement={active.placement} /> : null}
    </div>
  )
}
