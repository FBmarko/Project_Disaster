import { faultLines } from '../../data/faultFeatures.ts'
import type { FaultFeature } from '../../types/fault.ts'
import { PRECISION } from './projectTurkeyMap.ts'
import type { TurkeyMap } from './projectTurkeyMap.ts'

export type FaultPath = {
  feature: FaultFeature
  d: string
  anchor: { x: number; y: number }
}

export function projectFaultLines(features: readonly FaultFeature[], map: TurkeyMap): FaultPath[] {
  return features.map((feature) => {
    const lines = faultLines(feature.geometry).map((line) => line.map(map.projectPosition))
    const points = lines.flat()
    if (!points.length || points.some((point) => !point.every(Number.isFinite))) {
      throw new Error(`Non-finite projected fault: ${feature.id}`)
    }
    // A real in-window vertex anchors keyboard tooltips, even for border-crossing features.
    const inView = points.filter(([x, y]) => x >= 0 && x <= map.width && y >= 0 && y <= map.height)
    const [x, y] = inView[Math.floor(inView.length / 2)] ?? points[0]
    return {
      feature,
      d: lines.map((line) => `M${line.map(([px, py]) =>
        `${px.toFixed(PRECISION)},${py.toFixed(PRECISION)}`).join('L')}`).join(''),
      anchor: { x, y },
    }
  })
}
