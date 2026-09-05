/** Offline boundary/lifecycle checks. Numeric test inputs are not assembly-area records. */
import assert from 'node:assert/strict'
import { ASSEMBLY_AREAS, REGION_TEXT_LIMIT } from '../src/constants/assembly.ts'
import { TURKEY_PROVINCES } from '../src/constants/provinces.ts'
import { assemblyDirectionsUrl, hasValidAssemblyCoordinates, prepareAssemblyRegion } from '../src/utils/assemblyAreas.ts'
import { requestAssemblyLocation } from '../src/utils/assemblyGeolocation.ts'
import type { AssemblyCoordinates, AssemblyLocationStatus, AssemblyRegionDraft } from '../src/types/assembly.ts'

let checks = 0
function check(name: string, run: () => void) { run(); checks += 1; console.log(`PASS: ${name}`) }
const draft: AssemblyRegionDraft = { province: '', district: '', neighborhood: '' }

check('Initial source contains no assembly records or fixture locations', () => assert.deepEqual(ASSEMBLY_AREAS, []))
check('Empty/unknown provinces rejected; all 81 canonical provinces accepted', () => {
  assert.equal(TURKEY_PROVINCES.length, 81)
  assert.equal(new Set(TURKEY_PROVINCES).size, 81)
  assert.equal(prepareAssemblyRegion(draft).ok, false)
  assert.equal(prepareAssemblyRegion({ ...draft, province: 'Unknown' }).ok, false)
  for (const province of TURKEY_PROVINCES) assert.deepEqual(prepareAssemblyRegion({ ...draft, province }), {
    ok: true, search: { mode: 'REGION', province },
  })
})
check('Optional text is trimmed/omitted and bounded without inventing districts', () => {
  assert.deepEqual(prepareAssemblyRegion({ province: 'Ankara', district: '  ', neighborhood: '  ' }), {
    ok: true, search: { mode: 'REGION', province: 'Ankara' },
  })
  for (const field of ['district', 'neighborhood'] as const) {
    assert.equal(prepareAssemblyRegion({ ...draft, province: 'Ankara', [field]: 'x'.repeat(REGION_TEXT_LIMIT) }).ok, true)
    assert.equal(prepareAssemblyRegion({ ...draft, province: 'Ankara', [field]: 'x'.repeat(REGION_TEXT_LIMIT + 1) }).ok, false)
    assert.equal(prepareAssemblyRegion({ ...draft, province: 'Ankara', [field]: null } as unknown as AssemblyRegionDraft).ok, false)
  }
})
check('Missing/nonfinite/out-of-range coordinates never produce map or directions targets', () => {
  for (const point of [null, undefined, { latitude: NaN, longitude: 0 }, { latitude: 0, longitude: Infinity },
    { latitude: -91, longitude: 0 }, { latitude: 91, longitude: 0 }, { latitude: 0, longitude: -181 },
    { latitude: 0, longitude: 181 }, { latitude: '0', longitude: 0 } as unknown as AssemblyCoordinates]) {
    assert.equal(hasValidAssemblyCoordinates(point), false)
    assert.equal(assemblyDirectionsUrl(point), null)
  }
  for (const point of [{ latitude: 0, longitude: 0 }, { latitude: -90, longitude: -180 }, { latitude: 90, longitude: 180 }]) {
    assert.equal(hasValidAssemblyCoordinates(point), true)
    const url = new URL(assemblyDirectionsUrl(point)!)
    assert.equal(url.origin, 'https://www.google.com')
    assert.equal(url.pathname, '/maps/dir/')
    assert.equal(url.searchParams.get('destination'), `${point.latitude},${point.longitude}`)
    assert.equal(url.searchParams.get('api'), '1')
    assert.equal(url.searchParams.has('origin'), false)
  }
})

function locationHarness() {
  let success: PositionCallback | undefined
  let failure: PositionErrorCallback | null | undefined
  let options: PositionOptions | undefined
  let requests = 0
  const statuses: AssemblyLocationStatus[] = []
  const locations: AssemblyCoordinates[] = []
  const source: Pick<Geolocation, 'getCurrentPosition'> = {
    getCurrentPosition(onSuccess, onError, config) { requests += 1; success = onSuccess; failure = onError; options = config },
  }
  const callbacks = { onStatus: (status: AssemblyLocationStatus) => statuses.push(status), onLocation: (point: AssemblyCoordinates) => locations.push(point) }
  return {
    statuses, locations, source, callbacks,
    requests: () => requests,
    options: () => options,
    succeed: (latitude: number, longitude: number) => success?.({ coords: { latitude, longitude } } as GeolocationPosition),
    fail: (code: number) => failure?.({ code } as GeolocationPositionError),
  }
}

check('Location is requested once only on invocation, with bounded timeout and no watch', () => {
  const harness = locationHarness()
  assert.equal(harness.requests(), 0)
  requestAssemblyLocation(harness.source, harness.callbacks)
  assert.equal(harness.requests(), 1)
  assert.deepEqual(harness.statuses, ['loading'])
  assert.deepEqual(harness.options(), { enableHighAccuracy: false, timeout: 10_000, maximumAge: 0 })
  harness.succeed(0, 0)
  assert.deepEqual(harness.locations, [{ latitude: 0, longitude: 0 }])
  assert.deepEqual(harness.statuses, ['loading', 'success'])
  harness.succeed(1, 1)
  harness.fail(2)
  assert.equal(harness.locations.length, 1)
  assert.equal(harness.statuses.length, 2)
})
check('Denied, unavailable, timeout and unsupported states never retry automatically', () => {
  for (const [code, expected] of [[1, 'denied'], [2, 'unavailable'], [3, 'timeout'], [99, 'unavailable']] as const) {
    const harness = locationHarness()
    requestAssemblyLocation(harness.source, harness.callbacks)
    harness.fail(code)
    assert.deepEqual(harness.statuses, ['loading', expected])
    assert.equal(harness.requests(), 1)
    assert.deepEqual(harness.locations, [])
  }
  const harness = locationHarness()
  requestAssemblyLocation(undefined, harness.callbacks)
  assert.deepEqual(harness.statuses, ['unsupported'])
})
check('Cancellation drops late success/error callbacks after manual editing, replacement or unmount', () => {
  const harness = locationHarness()
  const cancel = requestAssemblyLocation(harness.source, harness.callbacks)
  cancel()
  harness.succeed(0, 0)
  harness.fail(1)
  assert.deepEqual(harness.locations, [])
  assert.deepEqual(harness.statuses, ['loading'])
})
check('Invalid browser coordinates and synchronous browser errors stay contained', () => {
  const harness = locationHarness()
  requestAssemblyLocation(harness.source, harness.callbacks)
  harness.succeed(NaN, Infinity)
  assert.deepEqual(harness.locations, [])
  assert.deepEqual(harness.statuses, ['loading', 'unavailable'])
  const statuses: AssemblyLocationStatus[] = []
  requestAssemblyLocation({ getCurrentPosition() { throw new Error('unavailable') } }, {
    onStatus: (status) => statuses.push(status), onLocation: () => assert.fail('No location expected'),
  })
  assert.deepEqual(statuses, ['loading', 'unavailable'])
})
console.log(`OK: ${checks} assembly checks passed. No location permissions, network, records or real coordinates used.`)
