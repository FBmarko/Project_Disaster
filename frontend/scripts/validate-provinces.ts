/**
 * Validates the bundled Turkey province dataset.
 *
 * Run with `npm run validate:provinces`. Uses the same name-resolution, grouping and
 * projection code as the application (`src/data/provinceFeatures.ts`,
 * `src/components/map/projectTurkeyMap.ts`), so a pass here means the map really does
 * resolve and draw all 81 provinces — not merely that the raw file has 81 rows.
 * Exits non-zero on any problem.
 */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  assertFeatureCollection,
  extractRings,
  groupFeaturesByProvince,
  readProvinceNameProperty,
} from '../src/data/provinceFeatures.ts'
import {
  TURKEY_PROVINCES,
  normalizeProvinceName,
  resolveProvinceName,
} from '../src/constants/provinces.ts'
import { projectProvinceShapes } from '../src/components/map/projectTurkeyMap.ts'

const DATA_PATH = fileURLToPath(
  new URL('../src/data/turkey-provinces.geojson', import.meta.url),
)

const problems: string[] = []
const fail = (message: string) => problems.push(message)

const raw = readFileSync(DATA_PATH, 'utf8')

// 1. No executable or otherwise unexpected content in a data file.
const SUSPICIOUS = ['<script', 'javascript:', 'eval(', 'require(', 'function(', '=>']
const found = SUSPICIOUS.filter((token) => raw.includes(token))
if (found.length > 0) fail(`Suspicious tokens in data file: ${found.join(', ')}`)

// 2. Valid FeatureCollection.
const parsed: unknown = JSON.parse(raw)
assertFeatureCollection(parsed)
const features = parsed.features
console.log(`FeatureCollection with ${features.length} features`)
if (features.length !== 81) fail(`Expected 81 features, found ${features.length}`)

// 3. Canonical list itself must be free of collisions after normalization.
if (new Set(TURKEY_PROVINCES).size !== 81) {
  fail(`Canonical province list has ${new Set(TURKEY_PROVINCES).size} unique names`)
}
const canonicalKeys = new Set(TURKEY_PROVINCES.map(normalizeProvinceName))
if (canonicalKeys.size !== 81) {
  fail(
    `Canonical names collide after normalization: ${canonicalKeys.size} distinct keys`,
  )
}

// 4. Every feature must carry a usable name and renderable geometry.
const featuresByProvince = new Map<string, string[]>()

features.forEach((feature, index) => {
  const rawName = readProvinceNameProperty(feature.properties)
  if (rawName === null) {
    fail(`Feature #${index} has no recognizable province name property`)
    return
  }

  const canonical = resolveProvinceName(rawName)
  if (canonical === null) {
    fail(`Feature #${index} name "${rawName}" does not resolve to a Turkish province`)
    return
  }

  const geometryType = feature.geometry?.type
  if (geometryType !== 'Polygon' && geometryType !== 'MultiPolygon') {
    fail(`"${canonical}" has unsupported geometry type ${String(geometryType)}`)
  }

  const rings = extractRings(feature.geometry)
  if (rings.length === 0) fail(`"${canonical}" has no rings`)
  if (rings.some((ring) => ring.length < 4)) {
    fail(`"${canonical}" has a ring with fewer than 4 positions`)
  }

  const list = featuresByProvince.get(canonical)
  if (list) list.push(rawName)
  else featuresByProvince.set(canonical, [rawName])
})

// 5. No province may be produced by more than one feature by accident, and none
//    may be missing. (Multipart geometry is fine — that is one feature.)
for (const [canonical, rawNames] of featuresByProvince) {
  if (rawNames.length > 1) {
    fail(`"${canonical}" is claimed by ${rawNames.length} features: ${rawNames.join(', ')}`)
  }
}

const missing = TURKEY_PROVINCES.filter((name) => !featuresByProvince.has(name))
if (missing.length > 0) fail(`Missing provinces: ${missing.join(', ')}`)

// 6. The grouped output the app actually renders.
const shapes = groupFeaturesByProvince(features)
console.log(`Resolved ${shapes.length} distinct provinces`)
if (shapes.length !== 81) fail(`Grouping produced ${shapes.length} provinces, expected 81`)
if (new Set(shapes.map((shape) => shape.name)).size !== shapes.length) {
  fail('Grouped output contains duplicate province names')
}

// 7. Coordinates must sit inside Turkey's real extent.
const EXPECTED_BOUNDS = { minLon: 25, maxLon: 45.5, minLat: 35, maxLat: 42.5 }
let minLon = Infinity
let maxLon = -Infinity
let minLat = Infinity
let maxLat = -Infinity
let positionCount = 0

for (const shape of shapes) {
  for (const ring of shape.rings) {
    for (const [lon, lat] of ring) {
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
        fail(`"${shape.name}" has a non-finite coordinate`)
        continue
      }
      positionCount += 1
      if (lon < minLon) minLon = lon
      if (lon > maxLon) maxLon = lon
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
    }
  }
}

console.log(
  `Bounds lon ${minLon.toFixed(3)}..${maxLon.toFixed(3)}, ` +
    `lat ${minLat.toFixed(3)}..${maxLat.toFixed(3)} (${positionCount} positions)`,
)

if (
  minLon < EXPECTED_BOUNDS.minLon ||
  maxLon > EXPECTED_BOUNDS.maxLon ||
  minLat < EXPECTED_BOUNDS.minLat ||
  maxLat > EXPECTED_BOUNDS.maxLat
) {
  fail('Coordinate bounds fall outside Turkey')
}

// 8. The projection the map renders must turn every shape into a drawable path.
const map = projectProvinceShapes(shapes)
console.log(
  `Projected ${map.provinces.length} paths into viewBox "${map.viewBox}" ` +
    `(aspect ${(map.width / map.height).toFixed(4)})`,
)

if (map.provinces.length !== shapes.length) {
  fail(`Projection produced ${map.provinces.length} paths for ${shapes.length} provinces`)
}

for (const province of map.provinces) {
  if (!province.d.startsWith('M') || !province.d.endsWith('Z')) {
    fail(`"${province.name}" produced malformed path data`)
  }
  if (province.d.includes('NaN')) fail(`"${province.name}" path data contains NaN`)
  if (!Number.isFinite(province.center.x) || !Number.isFinite(province.center.y)) {
    fail(`"${province.name}" has a non-finite tooltip anchor`)
  }
  if (
    province.center.x < 0 ||
    province.center.x > map.width ||
    province.center.y < 0 ||
    province.center.y > map.height
  ) {
    fail(`"${province.name}" tooltip anchor falls outside the viewBox`)
  }
}

// Turkey is roughly 2.3–2.4× wider than tall in Web Mercator; a wildly different
// ratio means the projection or the fit-to-viewBox scaling has broken.
const aspect = map.width / map.height
if (aspect < 2.0 || aspect > 2.8) fail(`Implausible map aspect ratio ${aspect.toFixed(3)}`)

// 9. Report renamed provinces so mapping changes stay visible.
const renamed = features
  .map((feature) => readProvinceNameProperty(feature.properties))
  .filter((name): name is string => name !== null)
  .map((rawName) => ({ rawName, canonical: resolveProvinceName(rawName) }))
  .filter((entry) => entry.canonical !== null && entry.canonical !== entry.rawName)

if (renamed.length > 0) {
  console.log('Dataset names mapped to canonical names:')
  for (const entry of renamed) console.log(`  ${entry.rawName} -> ${entry.canonical}`)
}

if (problems.length > 0) {
  console.error(`\n${problems.length} problem(s):`)
  for (const problem of problems) console.error(`  - ${problem}`)
  process.exit(1)
}

console.log('\nOK: all 81 provinces verified, no duplicates, no missing provinces.')
