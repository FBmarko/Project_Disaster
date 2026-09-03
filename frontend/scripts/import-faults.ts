/** Development-time, offline import. Never run downloaded repository scripts. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { parseFaultFeatures, provinceBounds, isTurkeyFault } from '../src/data/faultFeatures.ts'
import { assertFeatureCollection, groupFeaturesByProvince } from '../src/data/provinceFeatures.ts'

const SOURCE_SHA256 = '603513086b4693de6008e3444959995c34683b30dac291856340522a76d8505e'
const input = process.argv[2]
assert(input, 'Usage: node scripts/import-faults.ts <downloaded pinned gem_active_faults.geojson>')
const source = readFileSync(input)
assert.equal(createHash('sha256').update(source).digest('hex'), SOURCE_SHA256, 'Unexpected source version')
const raw: unknown = JSON.parse(source.toString('utf8'))
assertFeatureCollection(raw)
// Validate only the relevant catalog; unrelated global catalogs have missing/duplicate IDs.
const candidates = raw.features.filter((feature) => feature.properties?.catalog_name === 'EMME' &&
  typeof feature.properties?.catalog_id === 'string' && /^ME_TR/.test(feature.properties.catalog_id))
const normalized = parseFaultFeatures({ type: 'FeatureCollection', features: candidates })
const provinces: unknown = JSON.parse(readFileSync(new URL('../src/data/turkey-provinces.geojson', import.meta.url), 'utf8'))
assertFeatureCollection(provinces)
const bounds = provinceBounds(groupFeaturesByProvince(provinces.features))
const features = candidates.filter((_, index) => isTurkeyFault(normalized[index], bounds))
assert(features.length > 0)
const collection = { type: 'FeatureCollection', features }
const serialized = JSON.stringify(collection)
writeFileSync(new URL('../src/data/turkey-active-faults.geojson', import.meta.url), serialized + '\n')
const manifest = {
  dataset: 'GEM Global Active Faults Database',
  revision: '56816508ad92fd6846dad1163b1c8c01376a2cd1',
  sourceUrl: 'https://raw.githubusercontent.com/GEMScienceTools/gem-global-active-faults/56816508ad92fd6846dad1163b1c8c01376a2cd1/geojson/gem_active_faults.geojson',
  license: 'CC-BY-SA-4.0',
  sourceSha256: SOURCE_SHA256,
  accessed: '2026-09-03',
  filter: 'catalog_name === EMME; catalog_id starts ME_TR; at least one original vertex within the province bounding box (inclusive). Whole features retained in source order.',
  bounds,
  originalFeatureCount: raw.features.length,
  featureCount: features.length,
  coordinatesPreserved: true,
  canonicalSha256: createHash('sha256').update(serialized).digest('hex'),
}
writeFileSync(new URL('../src/data/turkey-active-faults.manifest.json', import.meta.url), JSON.stringify(manifest, null, 2) + '\n')
console.log(`Preserved ${features.length}/${raw.features.length} source features; ${serialized.length} bytes`)
