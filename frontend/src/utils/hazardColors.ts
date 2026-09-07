/**
 * Continuous color mapping for Peak Ground Acceleration (PGA in g).
 *
 * Implements mathematically continuous linear multi-stop interpolation between
 * the dataset minimum and maximum median PGA values. Provinces with higher
 * median PGA take deeper warm hues without categorical binning or discrete thresholds.
 */

type Rgb = readonly [number, number, number]

const STOPS: readonly { readonly t: number; readonly rgb: Rgb; readonly hex: string }[] = [
  { t: 0.0, rgb: [254, 240, 138], hex: '#FEF08A' }, // Light warm yellow
  { t: 0.35, rgb: [245, 158, 11], hex: '#F59E0B' }, // Amber
  { t: 0.7, rgb: [234, 88, 12], hex: '#EA580C' }, // Orange-red
  { t: 1.0, rgb: [153, 27, 27], hex: '#991B1B' }, // Deep crimson
]

function channelToHex(channel: number): string {
  const rounded = Math.max(0, Math.min(255, Math.round(channel)))
  return rounded.toString(16).padStart(2, '0')
}

function rgbToHex([r, g, b]: Rgb): string {
  return `#${channelToHex(r)}${channelToHex(g)}${channelToHex(b)}`
}

function lerp(start: number, end: number, factor: number): number {
  return start + factor * (end - start)
}

function interpolateRgb(start: Rgb, end: Rgb, factor: number): Rgb {
  return [
    lerp(start[0], end[0], factor),
    lerp(start[1], end[1], factor),
    lerp(start[2], end[2], factor),
  ]
}

export const HAZARD_NEUTRAL_FILL = '#F1F5F9'

/**
 * Maps a numeric PGA value to a continuous hex color between minPga and maxPga.
 *
 * - Returns neutral fill when pga is null or invalid.
 * - Handles minPga >= maxPga by returning mid-range color.
 * - Interpolates continuously without discrete classification buckets.
 */
export function pgaToContinuousColor(
  pga: number | null | undefined,
  minPga: number,
  maxPga: number,
): string {
  if (pga === null || pga === undefined || !Number.isFinite(pga)) {
    return HAZARD_NEUTRAL_FILL
  }

  if (minPga >= maxPga) {
    return STOPS[1].hex
  }

  // Normalize t to [0, 1]
  const rawT = (pga - minPga) / (maxPga - minPga)
  const t = Math.max(0, Math.min(1, rawT))

  // Find bounding stops
  for (let i = 0; i < STOPS.length - 1; i++) {
    const left = STOPS[i]
    const right = STOPS[i + 1]

    if (t >= left.t && t <= right.t) {
      const segmentSpan = right.t - left.t
      const localFactor = segmentSpan > 0 ? (t - left.t) / segmentSpan : 0
      return rgbToHex(interpolateRgb(left.rgb, right.rgb, localFactor))
    }
  }

  return STOPS[STOPS.length - 1].hex
}

/**
 * Returns a CSS linear-gradient string for legend rendering.
 */
export function getHazardGradientCss(): string {
  const stopsCss = STOPS.map((s) => `${s.hex} ${Math.round(s.t * 100)}%`).join(', ')
  return `linear-gradient(to right, ${stopsCss})`
}
