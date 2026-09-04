import assert from 'node:assert/strict'
import { parseFaultCollection } from '../src/api/faults.ts'
import { parseFaultEarthquakes } from '../src/api/earthquakes.ts'
import { parseAssemblyCollection } from '../src/api/assemblyAreas.ts'
import { assemblyDirectionsUrl } from '../src/utils/assemblyAreas.ts'

// Synthetic contract fixtures only. Never imported into application code or a database.
const id = '00000000-0000-0000-0000-000000000001'
const otherId = '00000000-0000-0000-0000-000000000002'
const fault = { type: 'Feature', id, geometry: { type: 'MultiLineString', coordinates: [[[0, 0], [1, 1]]] },
  properties: { id, source: 'GEM_GAF', source_feature_id: 'test-catalog', name: null, segment_name: null, fault_type: 'Normal', activity_status: null } }
const faults = { type: 'FeatureCollection', features: [fault], metadata: { count: 1, attribution: 'Test attribution', license: 'CC BY-SA 4.0' } }
const mapped = parseFaultCollection(faults)
assert.equal(mapped.features[0].id, id)
assert.equal(mapped.features[0].properties.sourceId, 'test-catalog')
assert.equal(mapped.features[0].properties.faultType, 'Normal')
assert.deepEqual(mapped.features[0].geometry, fault.geometry)
assert.equal(parseFaultCollection({ ...faults, features: [], metadata: { ...faults.metadata, count: 0 } }).features.length, 0)
assert.throws(() => parseFaultCollection({ ...faults, features: [fault, fault], metadata: { ...faults.metadata, count: 2 } }))
assert.throws(() => parseFaultCollection({ ...faults, features: [{ ...fault, properties: { ...fault.properties, id: otherId } }] }))
assert.throws(() => parseFaultCollection({ ...faults, features: [{ ...fault, geometry: { type: 'MultiLineString', coordinates: [[[0, 0], [Infinity, 0]]] } }] }))
assert.throws(() => parseFaultCollection({ ...faults, metadata: { ...faults.metadata, count: 3 } }))
console.log('PASS: fault UUID identity, unchanged geometry, metadata, empty collection and malformed/duplicate rejection')

const event = { type: 'Feature', id: otherId, geometry: { type: 'Point', coordinates: [0, 0] }, properties: {
  id: otherId, occurred_at: '2026-01-01T00:00:00Z', location_name: null, magnitude: 5.1, magnitude_type: 'ML', depth_km: 4,
  association_method: 'spatial_proximity', nearest_fault_id: id, distance_to_fault_km: 2,
} }
const events = { type: 'FeatureCollection', features: [event], metadata: { count: 1, fault_id: id, max_distance_km: 25,
  attribution: 'Test AFAD attribution', fault_attribution: 'Test GEM attribution', fault_license: 'CC BY-SA 4.0' } }
const history = parseFaultEarthquakes(events, id)
assert.equal(history.earthquakes[0].magnitudeType, 'ML')
assert.equal(history.earthquakes[0].location, null)
assert.equal(history.earthquakes[0].distanceKm, 2)
assert.throws(() => parseFaultEarthquakes(events, otherId))
assert.throws(() => parseFaultEarthquakes({ ...events, features: [{ ...event, properties: { ...event.properties, association_method: 'causal' } }] }, id))
assert.throws(() => parseFaultEarthquakes({ ...events, features: [{ ...event, properties: { ...event.properties, occurred_at: '2026-01-01' } }] }, id))
assert.equal(parseFaultEarthquakes({ ...events, features: [], metadata: { ...events.metadata, count: 0 } }, id).earthquakes.length, 0)
console.log('PASS: selected-fault/radius agreement, magnitude scale, null location, UTC dates and non-causal semantics')

const point = { type: 'Feature', id, geometry: { type: 'Point', coordinates: [0, 0] }, properties: {
  source_feature_id: 'node/test', name: null, ref: null, operator: 'AFAD', distance_km: 0,
} }
const polygon = { ...point, id: otherId, geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]] },
  properties: { ...point.properties, source_feature_id: 'way/test' } }
const assembly = { type: 'FeatureCollection', features: [point, polygon], metadata: { returned_count: 2, truncated: false,
  source: 'OpenStreetMap', source_classification: 'community_open_data', attribution: '© OpenStreetMap contributors',
  license: 'ODbL 1.0', source_data_timestamp: '2026-01-01T00:00:00Z' } }
const areas = parseAssemblyCollection(assembly)
assert.deepEqual(areas.areas[1].geometry, polygon.geometry)
assert.equal(areas.areas[1].latitude, undefined)
assert.equal(areas.areas[1].longitude, undefined)
assert.equal(areas.areas[1].province, undefined)
assert.equal(assemblyDirectionsUrl(areas.areas[1]), null)
assert.equal(new URL(assemblyDirectionsUrl(areas.areas[0])!).searchParams.get('destination'), '0,0')
assert.equal(new URL(assemblyDirectionsUrl(areas.areas[0])!).searchParams.has('origin'), false)
assert.equal(areas.areas[0].operator, 'AFAD') // operator is attribution, never official verification
assert.throws(() => parseAssemblyCollection({ ...assembly, features: [point, point] }))
assert.throws(() => parseAssemblyCollection({ ...assembly, features: [{ ...point, geometry: { type: 'Point', coordinates: [181, 0] } }] }))
assert.throws(() => parseAssemblyCollection({ ...assembly, features: [{ ...polygon, geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [2, 2]]] } }] }))
assert.equal(parseAssemblyCollection({ ...assembly, features: [], metadata: { ...assembly.metadata, returned_count: 0 } }).areas.length, 0)
console.log('PASS: Point/Polygon preservation, no invented entrances/addresses, metadata, empty records and malformed geometry rejection')
