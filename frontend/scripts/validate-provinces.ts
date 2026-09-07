/**
 * Validates the bundled Turkey province dataset.
 *
 * Run with `npm run validate:provinces`. Uses the same name-resolution, grouping and
 * projection code as the application (`src/data/provinceFeatures.ts`,
 * `src/components/map/projectTurkeyMap.ts`), so a pass here means the map really does
 * resolve and draw all 81 provinces — not merely that the raw file has 81 rows.
 * Exits non-zero on any problem.
 */

import { readFileSync, existsSync } from 'node:fs'
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
import {
  pgaToContinuousColor,
  getHazardGradientCss,
  HAZARD_NEUTRAL_FILL,
} from '../src/utils/hazardColors.ts'

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

// 10. Province Hazard API Contract & Mock Elimination (TASK 14B-F Section 26)

// 10a. Obsolete mock files must not exist
const obsoleteFiles = [
  '../src/data/mockProvinceRisk.ts',
  '../src/hooks/useProvinceRisk.ts',
  '../src/types/risk.ts',
  '../src/constants/colors.ts',
]
for (const rel of obsoleteFiles) {
  const fileLoc = fileURLToPath(new URL(rel, import.meta.url))
  if (existsSync(fileLoc)) {
    fail(`Obsolete mock file still exists: ${rel}`)
  }
}

// 10b. Required real hazard modules must exist
const requiredHazardFiles = [
  '../src/api/hazard.ts',
  '../src/hooks/useProvinceHazard.ts',
  '../src/types/hazard.ts',
  '../src/utils/hazardColors.ts',
]
for (const rel of requiredHazardFiles) {
  const fileLoc = fileURLToPath(new URL(rel, import.meta.url))
  if (!existsSync(fileLoc)) {
    fail(`Required hazard module missing: ${rel}`)
  }
}

// 10c. Verify backend/frontend GeoJSON parity if backend file present
const backendGeoJsonPath = fileURLToPath(new URL('../../backend/data/turkey_provinces.geojson', import.meta.url))
if (existsSync(backendGeoJsonPath)) {
  const backendRaw = readFileSync(backendGeoJsonPath, 'utf8')
  if (backendRaw !== raw) {
    fail('Backend turkey_provinces.geojson does not match frontend turkey-provinces.geojson')
  } else {
    console.log('Parity verified: backend and frontend province GeoJSONs are byte-for-byte identical.')
  }
}

// 10d. Continuous color interpolation test (no NaN, safe on min == max, monotonic)
const hexPattern = /^#[0-9A-Fa-f]{6}$/
if (!hexPattern.test(HAZARD_NEUTRAL_FILL)) {
  fail(`Invalid neutral fill hex: ${HAZARD_NEUTRAL_FILL}`)
}
const c0 = pgaToContinuousColor(0.1, 0.1, 0.5)
const cMid = pgaToContinuousColor(0.3, 0.1, 0.5)
const c1 = pgaToContinuousColor(0.5, 0.1, 0.5)
const cSame = pgaToContinuousColor(0.25, 0.25, 0.25)
const cNull = pgaToContinuousColor(null, 0.1, 0.5)

if (!hexPattern.test(c0) || !hexPattern.test(cMid) || !hexPattern.test(c1)) {
  fail(`Interpolated color returned invalid hex: c0=${c0}, cMid=${cMid}, c1=${c1}`)
}
if (c0 === c1) {
  fail('Interpolated color is not varying across domain')
}
if (!hexPattern.test(cSame)) {
  fail(`min == max returned invalid hex: ${cSame}`)
}
if (cNull !== HAZARD_NEUTRAL_FILL) {
  fail(`null PGA did not return HAZARD_NEUTRAL_FILL (${HAZARD_NEUTRAL_FILL}), got ${cNull}`)
}
const gradCss = getHazardGradientCss()
if (!gradCss.includes('linear-gradient')) {
  fail(`getHazardGradientCss did not return a valid linear-gradient: ${gradCss}`)
}

// 10e. Static audit of map components: ensure no mock risk rotation or categorical risk labels
const mapFiles = [
  '../src/components/map/TurkeyRiskMap.tsx',
  '../src/components/map/ProvinceTooltip.tsx',
  '../src/components/map/RiskLegend.tsx',
  '../src/pages/HomePage.tsx',
]
for (const rel of mapFiles) {
  const content = readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8')
  if (content.includes('mockProvinceRisk') || content.includes('useProvinceRisk')) {
    fail(`Component ${rel} still references obsolete mock risk hooks/data`)
  }
  if (content.includes('% 3') || content.includes('Düşük Risk') || content.includes('Yüksek Risk')) {
    fail(`Component ${rel} still references mock modulo rotation or categorical risk labels`)
  }
}

// Verify tooltip and disclaimer contents
const tooltipContent = readFileSync(fileURLToPath(new URL('../src/components/map/ProvinceTooltip.tsx', import.meta.url)), 'utf8')
if (!tooltipContent.includes('Medyan PGA') || !tooltipContent.includes('PGA Aralığı') || !tooltipContent.includes('Grid Noktası')) {
  fail('ProvinceTooltip does not expose required numeric hazard fields')
}
const homeContent = readFileSync(fileURLToPath(new URL('../src/pages/HomePage.tsx', import.meta.url)), 'utf8')
if (!homeContent.includes('GEM GSHM v2026.1') || !homeContent.includes('Vs30 = 800 m/s') || !homeContent.includes('AFAD')) {
  fail('HomePage does not display required scientific hazard disclaimer and AFAD attribution')
}

if (problems.length > 0) {
  console.error(`\n${problems.length} problem(s):`)
  for (const problem of problems) console.error(`  - ${problem}`)
  process.exit(1)
}

console.log('\nOK: all 81 provinces verified, hazard contract and continuous gradient verified, no mock risk rotation.')
