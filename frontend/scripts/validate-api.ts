import assert from 'node:assert/strict'
import { parseFaultCollection } from '../src/api/faults.ts'
import { parseFaultEarthquakes } from '../src/api/earthquakes.ts'
import { parseAssemblyCollection } from '../src/api/assemblyAreas.ts'
import { parseProvinceHazards } from '../src/api/hazard.ts'
import { parseScenarioResponse } from '../src/api/scenario.ts'
import { ApiError, resolveApiUrl } from '../src/api/client.ts'
import { assemblyDirectionsUrl } from '../src/utils/assemblyAreas.ts'
import { TURKEY_PROVINCES } from '../src/constants/provinces.ts'

// Synthetic contract fixtures only. Never imported into application code or a database.
const id = '00000000-0000-0000-0000-000000000001'
const otherId = '00000000-0000-0000-0000-000000000002'
const fault = { type: 'Feature', id, geometry: { type: 'MultiLineString', coordinates: [[[0, 0], [1, 1]]] },
  properties: { id, source: 'GEM_GAF', source_feature_id: 'test-catalog', name: null, segment_name: null, fault_type: 'Normal', activity_status: null } }
const faults = { type: 'FeatureCollection', features: [fault], metadata: { count: 1, attribution: 'Test attribution', license: 'CC BY-SA 4.0' } }
const mapped = parseFaultCollection(faults)
assert.equal(mapped.features[0].id, id)
assert.equal(mapped.features[0].properties.sourceId, 'test-catalog')
assert.equal(mapped.features[0].properties.displayName, 'Fay Segmenti · test-catalog')
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

const syntheticProvinces = TURKEY_PROVINCES.map((provinceName, index) => {
  const plate = index + 1
  const provinceId = plate.toString().padStart(2, '0')
  return {
    province_id: provinceId,
    plate_code: plate,
    province_name: provinceName,
    sample_count: 50,
    min_pga_g: 0.1,
    median_pga_g: 0.2 + (plate / 1000),
    max_pga_g: 0.5,
  }
})

const hazardPayload = {
  dataset: {
    source: 'GEM_GSHM',
    source_version: '2026.1',
    model_name: 'Global Seismic Hazard Map',
    version_doi: '10.5281/zenodo.20735384',
    license: 'CC BY-NC-SA 4.0',
    attribution: 'Global Earthquake Model Foundation',
  },
  metric: {
    name: 'PGA',
    unit: 'g',
    return_period_years: 475,
    exceedance_probability: 0.1,
    time_horizon_years: 50,
    reference_vs30_mps: 800,
    reference_ground: 'Reference Rock',
  },
  summary_method: 'province_grid_median',
  provinces: syntheticProvinces,
  boundary_source: 'alpers/Turkey-Maps-GeoJSON (Apache-2.0)',
  disclaimer: 'Bu gösterim GEM GSHM v2026.1 verisidir.',
}

const parsedHazards = parseProvinceHazards(hazardPayload)
assert.equal(parsedHazards.provinces.length, 81)
assert.equal(parsedHazards.provincesByName['Adana'].plateCode, 1)
assert.equal(parsedHazards.provincesByName['Düzce'].plateCode, 81)
assert.equal(Number.isFinite(parsedHazards.minMedianPga), true)
assert.equal(Number.isFinite(parsedHazards.maxMedianPga), true)
assert.equal(parsedHazards.minMedianPga <= parsedHazards.maxMedianPga, true)

// Rejections
assert.throws(() => parseProvinceHazards({ ...hazardPayload, provinces: syntheticProvinces.slice(0, 80) }))
assert.throws(() => parseProvinceHazards({ ...hazardPayload, provinces: [...syntheticProvinces, syntheticProvinces[0]] }))
assert.throws(() => parseProvinceHazards({
  ...hazardPayload,
  provinces: [{ ...syntheticProvinces[0], min_pga_g: 0.9, median_pga_g: 0.2 }, ...syntheticProvinces.slice(1)],
}))
assert.throws(() => parseProvinceHazards({
  ...hazardPayload,
  provinces: [{ ...syntheticProvinces[0], max_pga_g: 0.1, median_pga_g: 0.2 }, ...syntheticProvinces.slice(1)],
}))
console.log('PASS: province hazard API contract, 81 unique provinces, min/median/max invariants, and malformed rejection')

// Unit tests for API URL resolution and error handling
// CASE A: VITE_API_BASE_URL absent or blank -> relative path
assert.equal(resolveApiUrl('/api/v1/health'), '/api/v1/health')
assert.equal(resolveApiUrl('/api/v1/health', undefined), '/api/v1/health')
assert.equal(resolveApiUrl('/api/v1/health', ''), '/api/v1/health')
assert.equal(resolveApiUrl('/api/v1/health', '   '), '/api/v1/health')
assert.equal(resolveApiUrl('api/v1/health', ''), '/api/v1/health')

// CASE B: base configured without trailing slash
assert.equal(resolveApiUrl('/api/v1/health', 'https://api.example.com'), 'https://api.example.com/api/v1/health')

// CASE C: base configured with single or multiple trailing slashes
assert.equal(resolveApiUrl('/api/v1/health', 'https://api.example.com/'), 'https://api.example.com/api/v1/health')
assert.equal(resolveApiUrl('/api/v1/health', 'https://api.example.com///'), 'https://api.example.com/api/v1/health')
assert.equal(resolveApiUrl('api/v1/health', 'https://api.example.com/'), 'https://api.example.com/api/v1/health')

// CASE D: ApiError type and status preservation
const defaultErr = new ApiError()
assert.equal(defaultErr instanceof Error, true)
assert.equal(defaultErr.name, 'ApiError')
assert.equal(defaultErr.status, null)
assert.equal(defaultErr.message, 'Project API request failed')

const statusErr = new ApiError(404)
assert.equal(statusErr.status, 404)
assert.equal(statusErr instanceof ApiError, true)

console.log('PASS: API base URL resolution (absent, configured, trailing-slash) and ApiError semantics')

// Deterministic Scenario Calculation API contract
const validScenarioPayload = {
  model: {
    name: 'Akkar et al. (2014) Rhyp Point-Source GMPE',
    citation: 'Akkar, S., Sandıkkaya, M. A., & Bommer, J. J. (2014). Empirical ground-motion models for point- and extended-source crustal earthquake scenarios in Europe and the Middle East. Bulletin of Earthquake Engineering, 12(1), 359-387.',
    doi: '10.1007/s10518-013-9461-4',
    tectonic_region: 'active_shallow_crust',
    component: 'geometric_mean_horizontal',
    intensity_measure: 'PGA',
    unit: 'g',
  },
  scenario: {
    epicenter: { latitude: 38.0, longitude: 35.0 },
    magnitude_mw: 6.5,
    depth_km: 10.0,
    mechanism: 'strike_slip',
    rake_degrees: 0.0,
    vs30_m_s: 800.0,
    max_surface_distance_km: 150.0,
  },
  model_scope: {
    af360_magnitude_guard: [4.0, 7.6],
    max_rhypo_km: 200.0,
    max_focal_depth_km: 30.0,
    vs30_m_s: [150.0, 1200.0],
  },
  total_sigma_ln: 0.7347136109315354,
  epicenter_estimate: {
    surface_distance_km: 0.0,
    rhypo_km: 10.0,
    median_pga_g: 0.4273348472,
    minus_1sigma_pga_g: 0.2049363842,
    plus_1sigma_pga_g: 0.8911048604,
  },
  profile_step_km: 5.0,
  radial_profile: [
    {
      surface_distance_km: 0.0,
      rhypo_km: 10.0,
      median_pga_g: 0.4273348472,
      minus_1sigma_pga_g: 0.2049363842,
      plus_1sigma_pga_g: 0.8911048604,
    },
    {
      surface_distance_km: 5.0,
      rhypo_km: 11.18033988749895,
      median_pga_g: 0.385,
      minus_1sigma_pga_g: 0.185,
      plus_1sigma_pga_g: 0.802,
    },
  ],
  disclaimer: 'Bu senaryo simülasyonu, seçilen parametrelere dayalı deterministik yer hareketi tahmin modelidir (Akkar et al., 2014). Deprem tahmini, bina hasarı veya can kaybı riski içermez. Mühendislik hesapları yerine kullanılamaz.',
}

const parsedScenario = parseScenarioResponse(validScenarioPayload)
assert.equal(parsedScenario.model.name, 'Akkar et al. (2014) Rhyp Point-Source GMPE')
assert.equal(parsedScenario.scenario.magnitudeMw, 6.5)
assert.equal(parsedScenario.scenario.mechanism, 'strike_slip')
assert.equal(parsedScenario.radialProfile.length, 2)
assert.equal(parsedScenario.radialProfile[0].surfaceDistanceKm, 0.0)
assert.equal(parsedScenario.radialProfile[0].medianPgaG, 0.4273348472)

// Malformed rejection
assert.throws(() => parseScenarioResponse({ ...validScenarioPayload, scenario: { ...validScenarioPayload.scenario, mechanism: 'oblique' } }))
assert.throws(() => parseScenarioResponse({ ...validScenarioPayload, radial_profile: [] }))
console.log('PASS: deterministic scenario simulation response schema, radial profile, and rejection of unknown mechanisms/empty profiles')
