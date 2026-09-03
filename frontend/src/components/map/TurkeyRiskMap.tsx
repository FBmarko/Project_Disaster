import { useCallback, useRef, useState } from 'react'
import { ProvinceTooltip } from '@/components/map/ProvinceTooltip'
import { TURKEY_MAP } from '@/components/map/turkeyMapGeometry'
import type { ProvincePath } from '@/components/map/turkeyMapGeometry'
import { RISK_COLORS } from '@/constants/colors'
import { RISK_LEVEL_LABELS } from '@/types/risk'
import type { ProvinceRiskMap, RiskLevel } from '@/types/risk'

type TurkeyRiskMapProps = {
  /** Province → risk lookup. Missing provinces stay neutral. */
  riskByProvince: ProvinceRiskMap
}

type ActiveProvince = {
  province: ProvincePath
  level: RiskLevel | null
  /** Tooltip anchor, in pixels relative to the map container. */
  x: number
  y: number
  containerWidth: number
  containerHeight: number
}

/** Provinces are near-white until hovered, as in the design reference. */
const NEUTRAL_FILL = '#FFFFFF'
const BORDER_COLOR = '#1F2937'

/**
 * Interactive province map of Turkey.
 *
 * Boundaries come from the bundled GeoJSON, pre-projected into SVG path data at
 * module load (`turkeyMapGeometry`). The SVG is sized by its viewBox, so it scales
 * to any container width without distortion and without re-projecting.
 *
 * Every province is its own `<path>`: hoverable, focusable, and independently
 * coloured. Only the active province takes a risk colour; the rest stay neutral.
 */
export function TurkeyRiskMap({ riskByProvince }: TurkeyRiskMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState<ActiveProvince | null>(null)

  const clear = useCallback(() => setActive(null), [])

  /** Anchor from a pointer event, in container-relative pixels. */
  const activateAtPointer = useCallback(
    (province: ProvincePath, clientX: number, clientY: number) => {
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return

      setActive({
        province,
        level: riskByProvince[province.name] ?? null,
        x: clientX - rect.left,
        y: clientY - rect.top,
        containerWidth: rect.width,
        containerHeight: rect.height,
      })
    },
    [riskByProvince],
  )

  /**
   * Keyboard equivalent: anchor the tooltip at the province's centre. The SVG fills
   * the container width, so viewBox units convert with a single uniform scale.
   */
  const activateAtCenter = useCallback(
    (province: ProvincePath) => {
      const rect = containerRef.current?.getBoundingClientRect()
      if (!rect) return

      const scale = rect.width / TURKEY_MAP.width

      setActive({
        province,
        level: riskByProvince[province.name] ?? null,
        x: province.center.x * scale,
        y: province.center.y * scale,
        containerWidth: rect.width,
        containerHeight: rect.height,
      })
    },
    [riskByProvince],
  )

  return (
    <div ref={containerRef} className="relative w-full" onPointerLeave={clear}>
      <p className="sr-only">
        Türkiye il haritası. Bir ilin üzerine gelin veya klavyeyle odaklanın; ilin
        risk seviyesi renklenir ve adı ile risk düzeyi gösterilir.
      </p>

      <svg
        viewBox={TURKEY_MAP.viewBox}
        className="block h-auto w-full"
        role="group"
        aria-label="Türkiye il bazlı deprem risk haritası"
      >
        <g onPointerLeave={clear}>
          {TURKEY_MAP.provinces.map((province) => {
            const level = riskByProvince[province.name] ?? null
            const isActive = active?.province.name === province.name

            return (
              <path
                key={province.name}
                d={province.d}
                fillRule="evenodd"
                fill={isActive && level ? RISK_COLORS[level] : NEUTRAL_FILL}
                stroke={BORDER_COLOR}
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
                tabIndex={0}
                role="img"
                aria-label={`${province.name}: ${
                  level ? RISK_LEVEL_LABELS[level] : 'Risk verisi yok'
                }`}
                className="cursor-pointer transition-colors duration-150"
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
          level={active.level}
          placement={{ x: active.x, y: active.y }}
          containerWidth={active.containerWidth}
          containerHeight={active.containerHeight}
        />
      ) : null}
    </div>
  )
}
