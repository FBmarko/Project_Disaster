/** Runs offline against the same asset, adapter and projection as the UI. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { faultLines, isTurkeyFault, parseFaultFeatures, provinceBounds } from '../src/data/faultFeatures.ts'
import { assertFeatureCollection, groupFeaturesByProvince } from '../src/data/provinceFeatures.ts'
import { projectProvinceShapes } from '../src/components/map/projectTurkeyMap.ts'
import { projectFaultLines } from '../src/components/map/projectFaultLines.ts'

const read = (path: string): unknown => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'))
const canonicalHash = (value: unknown) => createHash('sha256').update(JSON.stringify(value)).digest('hex')
const raw = read('../src/data/turkey-active-faults.geojson')
const features = parseFaultFeatures(raw)
assertFeatureCollection(raw)
const manifest = read('../src/data/turkey-active-faults.manifest.json') as {
  featureCount: number; canonicalSha256: string; bounds: unknown; license: string
}
assert.equal(features.length, 321, 'Unexpected pinned subset size')
assert.equal(features.length, manifest.featureCount)
assert.equal(canonicalHash(raw), manifest.canonicalSha256, 'Bundled data differs from the preserved source subset')
assert.equal(manifest.license, 'CC-BY-SA-4.0')
assert.equal(new Set(features.map((feature) => feature.id)).size, features.length)

const provinces = read('../src/data/turkey-provinces.geojson')
assertFeatureCollection(provinces)
const shapes = groupFeaturesByProvince(provinces.features)
const bounds = provinceBounds(shapes)
assert.deepEqual(bounds, manifest.bounds, 'Filter window must match the actual province data')
const map = projectProvinceShapes(shapes)
// Captured before the shared transform was exposed. Includes every path and tooltip anchor.
assert.equal(canonicalHash(map), '75349a5ae63ab5ec4d6ad51daf2a7bfc18cd7404e5a5624e875bceaa2312f3a5',
  'HomePage geometry, tooltip anchors or aspect ratio changed')
const paths = projectFaultLines(features, map)
assert.equal(paths.length, features.length, 'Every included feature must render')
let positionCount = 0
for (const [index, feature] of features.entries()) {
  assert(isTurkeyFault(feature, bounds), `Unintended out-of-scope feature ${feature.id}`)
  assert.equal(feature.id, feature.properties.sourceId)
  assert(feature.properties.displayName.length > 0)
  const lines = faultLines(feature.geometry)
  const path = paths[index]
  assert.equal(path.feature.id, feature.id)
  assert.equal((path.d.match(/M/g) ?? []).length, lines.length, 'Multipart segments must stay separate')
  assert(!/NaN|Infinity|Z/.test(path.d), 'Fault paths must be finite and open')
  assert(/^M[-\d.,LM]+$/.test(path.d))
  assert(Number.isFinite(path.anchor.x) && Number.isFinite(path.anchor.y))
  assert(path.anchor.x >= 0 && path.anchor.x <= map.width && path.anchor.y >= 0 && path.anchor.y <= map.height)
  for (const line of lines) {
    positionCount += line.length
    const projected = line.map(map.projectPosition)
    assert(projected.every((point) => point.every(Number.isFinite)))
    assert(new Set(projected.map((point) => point.map((n) => n.toFixed(2)).join(','))).size > 1,
      `Fault ${feature.id} collapsed at display precision`)
  }
}

// Boundary cases use copies of REAL source positions; no synthetic geographic traces.
const first = raw.features[0]
assert(first.geometry && first.properties)
const realLine = faultLines(features[0].geometry)[0]
const multipart = { ...first, geometry: { type: 'MultiLineString', coordinates: [realLine, realLine] } }
assert.equal((projectFaultLines(parseFaultFeatures({ type: 'FeatureCollection', features: [multipart] }), map)[0].d.match(/M/g) ?? []).length, 2)
for (const badGeometry of [null, { type: 'Polygon', coordinates: [realLine] },
  { type: 'LineString', coordinates: [] }, { type: 'MultiLineString', coordinates: [[]] },
  { type: 'LineString', coordinates: [[NaN, realLine[0][1]], realLine[1]] },
  { type: 'LineString', coordinates: [[Infinity, realLine[0][1]], realLine[1]] }]) {
  assert.throws(() => parseFaultFeatures({ type: 'FeatureCollection', features: [{ ...first, geometry: badGeometry }] }))
}
assert.throws(() => parseFaultFeatures({ type: 'FeatureCollection', features: [] }))
assert.throws(() => parseFaultFeatures({ type: 'FeatureCollection', features: [first, first] }))
assert.throws(() => parseFaultFeatures({ type: 'FeatureCollection', features: [{ ...first, properties: {} }] }))
const unnamed = parseFaultFeatures({ type: 'FeatureCollection', features: [{ ...first, properties: { ...first.properties, name: { unexpected: true } } }] })[0]
assert.equal(unnamed.properties.displayName, 'Adsız Fay Segmenti')
assert.equal(unnamed.properties.sourceName, null)

// Optional provenance audit against the original pinned download (no network).
if (process.argv[2]) {
  const source: unknown = JSON.parse(readFileSync(process.argv[2], 'utf8'))
  assertFeatureCollection(source)
  const originals = new Map(source.features.map((feature) => [feature.properties?.catalog_id, feature]))
  for (const feature of raw.features) assert.deepEqual(feature, originals.get(feature.properties?.catalog_id))
  console.log('Original source audit: every included feature, property and coordinate is unchanged.')
}
console.log(`OK: ${features.length} real source features, ${positionCount} positions, ${paths.length} finite SVG paths.`)
console.log(`Geometry: ${[...new Set(features.map((feature) => feature.geometry.type))].join(', ')}; MultiLineString adapter/projection verified.`)
console.log('Turkey filter, IDs, safe names, integrity, invalid-data rejection and exact HomePage projection baseline verified.')
