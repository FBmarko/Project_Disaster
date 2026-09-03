import type { Position, ProvinceShape } from '../../data/provinceFeatures.ts'

/**
 * Projects province boundaries into SVG path data.
 *
 * A Web Mercator projection is applied and then uniformly scaled to fit a fixed
 * viewBox. Because the scale is uniform and the SVG is sized by its viewBox, the
 * map keeps Turkey's true aspect ratio at every viewport width — the browser does
 * the responsive scaling, and no re-projection happens on resize.
 *
 * This replaces a mapping library: the whole projection is a few dozen lines, so no
 * extra dependency is warranted for a static thematic map.
 *
 * Kept free of bundler-specific imports (no `?raw`, no `@/` alias) so that
 * `scripts/validate-provinces.ts` can exercise the exact projection the map renders.
 * Explicit `.ts` extensions are required for Node to run this module directly.
 */

/** Horizontal extent of the generated viewBox, in SVG user units. */
export const VIEWBOX_WIDTH = 1000

/** Coordinate precision in the emitted path data; ~0.1 px at typical sizes. */
export const PRECISION = 2

const DEG_TO_RAD = Math.PI / 180

type Point = readonly [number, number]

/** Web Mercator, with y already flipped for screen coordinates. */
function project([lon, lat]: Position): Point {
  const clampedLat = Math.max(-85, Math.min(85, lat))
  const x = lon * DEG_TO_RAD
  const y = Math.log(Math.tan(Math.PI / 4 + (clampedLat * DEG_TO_RAD) / 2))
  return [x, -y]
}

function signedArea(ring: readonly Point[]): number {
  let sum = 0
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    sum += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1]
  }
  return sum / 2
}

/** Area-weighted centroid of a closed ring, falling back to its first vertex. */
function centroidOf(ring: readonly Point[]): Point {
  const area = signedArea(ring)
  if (area === 0) return ring[0]

  let x = 0
  let y = 0
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const cross = ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1]
    x += (ring[j][0] + ring[i][0]) * cross
    y += (ring[j][1] + ring[i][1]) * cross
  }

  return [x / (6 * area), y / (6 * area)]
}

export type ProvincePath = {
  /** Canonical Turkish province name. */
  name: string
  /** SVG path data covering every ring of the province. */
  d: string
  /** Centre of the province's largest ring, in viewBox units. */
  center: { x: number; y: number }
}

export type TurkeyMap = {
  width: number
  height: number
  /** Ready-to-use `viewBox` attribute value. */
  viewBox: string
  provinces: ProvincePath[]
}

export function projectProvinceShapes(shapes: readonly ProvinceShape[]): TurkeyMap {
  const projected = shapes.map((shape) => ({
    name: shape.name,
    rings: shape.rings.map((ring) => ring.map(project)),
  }))

  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  for (const province of projected) {
    for (const ring of province.rings) {
      for (const [x, y] of ring) {
        if (x < minX) minX = x
        if (x > maxX) maxX = x
        if (y < minY) minY = y
        if (y > maxY) maxY = y
      }
    }
  }

  const spanX = maxX - minX
  const spanY = maxY - minY

  // Empty or degenerate dataset: fail loudly rather than emit a broken viewBox.
  if (!Number.isFinite(spanX) || spanX <= 0 || spanY <= 0) {
    throw new Error('Turkey province geometry is empty or degenerate')
  }

  const scale = VIEWBOX_WIDTH / spanX
  const height = spanY * scale

  const toViewBox = ([x, y]: Point): Point => [(x - minX) * scale, (y - minY) * scale]

  const provinces: ProvincePath[] = projected.map((province) => {
    const rings = province.rings.map((ring) => ring.map(toViewBox))

    const d = rings
      .map(
        (ring) =>
          `M${ring
            .map(([x, y]) => `${x.toFixed(PRECISION)},${y.toFixed(PRECISION)}`)
            .join('L')}Z`,
      )
      .join('')

    const largestRing = rings.reduce((largest, ring) =>
      Math.abs(signedArea(ring)) > Math.abs(signedArea(largest)) ? ring : largest,
    )
    const [cx, cy] = centroidOf(largestRing)

    return { name: province.name, d, center: { x: cx, y: cy } }
  })

  return {
    width: VIEWBOX_WIDTH,
    height,
    viewBox: `0 0 ${VIEWBOX_WIDTH} ${height.toFixed(PRECISION)}`,
    provinces,
  }
}
