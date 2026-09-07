import { useCallback, useRef, useState } from 'react'
import { ProvinceTooltip } from '@/components/map/ProvinceTooltip'
import { TURKEY_MAP } from '@/components/map/turkeyMapGeometry'
import type { ProvincePath } from '@/components/map/turkeyMapGeometry'
import type { ProvinceHazardCollection, ProvinceHazardItem } from '@/types/hazard'
import { HAZARD_NEUTRAL_FILL, pgaToContinuousColor } from '@/utils/hazardColors'

type TurkeyRiskMapProps = {
  /** Aggregated province hazard collection from GEM GSHM v2026.1 dataset. */
  readonly hazards?: ProvinceHazardCollection | null
  readonly isLoading?: boolean
}

type ActiveProvince = {
  readonly province: ProvincePath
  readonly hazard: ProvinceHazardItem | null
  readonly x: number
  readonly y: number
  readonly containerWidth: number
  readonly containerHeight: number
}

const BORDER_COLOR = 'var(--color-map-border, #CBD5E1)'
const ACTIVE_BORDER_COLOR = '#0F172A'

/**
 * Interactive province map of Turkey displaying continuous PGA hazard data.
 *
 * Each province is rendered as an SVG path filled according to its spatial
 * median PGA value interpolated continuously between minimum and maximum dataset
 * bounds. Hovering or focusing displays detailed numeric metrics in a tooltip.
 */
export function TurkeyRiskMap({ hazards, isLoading }: TurkeyRiskMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState<ActiveProvince | null>(null)

  const clear = useCallback(() => setActive(null), [])

  const activateAtPointer = useCallback(
    (province: ProvincePath, clientX: number, clientY: number) => {
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return

      const hazard = hazards?.provincesByName[province.name] ?? null

      setActive({
        province,
        hazard,
        x: clientX - rect.left,
        y: clientY - rect.top,
        containerWidth: rect.width,
        containerHeight: rect.height,
      })
    },
    [hazards],
  )

  const activateAtCenter = useCallback(
    (province: ProvincePath) => {
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return

      const scale = rect.width / TURKEY_MAP.width
      const hazard = hazards?.provincesByName[province.name] ?? null

      setActive({
        province,
        hazard,
        x: province.center.x * scale,
        y: province.center.y * scale,
        containerWidth: rect.width,
        containerHeight: rect.height,
      })
    },
    [hazards],
  )

  return (
    <div ref={containerRef} className="relative w-full" onPointerLeave={clear}>
      <p className="sr-only">
        Türkiye il deprem tehlike haritası. Bir ilin üzerine gelin veya klavyeyle
        odaklanın; ilin medyan PGA değeri ve tehlike aralığı gösterilir.
      </p>

      <svg
        viewBox={TURKEY_MAP.viewBox}
        className={`block h-auto w-full transition-opacity duration-200 ${
          isLoading ? 'opacity-60' : 'opacity-100'
        }`}
        role="group"
        aria-label="Türkiye il bazlı deprem tehlike haritası"
      >
        <g onPointerLeave={clear}>
          {TURKEY_MAP.provinces.map((province) => {
            const item = hazards?.provincesByName[province.name] ?? null
            const isActive = active?.province.name === province.name

            const fillColor =
              item && item.medianPgaG !== null && hazards
                ? pgaToContinuousColor(
                    item.medianPgaG,
                    hazards.minMedianPga,
                    hazards.maxMedianPga,
                  )
                : HAZARD_NEUTRAL_FILL

            const label =
              item && item.medianPgaG !== null
                ? `${province.name}: ${item.medianPgaG.toFixed(3)} g medyan PGA`
                : `${province.name}: Tehlike verisi yok`

            return (
              <path
                key={province.name}
                d={province.d}
                fillRule="evenodd"
                fill={fillColor}
                stroke={isActive ? ACTIVE_BORDER_COLOR : BORDER_COLOR}
                strokeWidth={isActive ? 1.75 : 0.75}
                vectorEffect="non-scaling-stroke"
                tabIndex={0}
                role="img"
                aria-label={label}
                className="cursor-pointer transition-all duration-150 hover:brightness-105"
                onPointerEnter={(event) =>
                  activateAtPointer(province, event.clientX, event.clientY)
                }
                onPointerMove={(event) =>
                  activateAtPointer(province, event.clientX, event.clientY)
                }
                onFocus={() => activateAtCenter(province)}
                onBlur={clear}
              />
            )
          })}
        </g>
      </svg>

      {active ? (
        <ProvinceTooltip
          province={active.province.name}
          hazard={active.hazard}
          placement={{ x: active.x, y: active.y }}
          containerWidth={active.containerWidth}
          containerHeight={active.containerHeight}
        />
      ) : null}
    </div>
  )
}

export const TurkeyHazardMap = TurkeyRiskMap
