import { useCallback, useRef, useState } from 'react'
import { AssemblyAreaMap } from '@/components/assembly/AssemblyAreaMap'
import { AssemblyAreaSearchPanel } from '@/components/assembly/AssemblyAreaSearchPanel'
import { AssemblyAreaList } from '@/components/assembly/AssemblyAreaList'
import { AssemblyAreaSafetyNotice } from '@/components/assembly/AssemblyAreaSafetyNotice'
import { getNearbyAssemblyAreas } from '@/api/assemblyAreas'
import { useApiResource } from '@/hooks/useApiResource'
import { useAssemblyLocation } from '@/hooks/useAssemblyLocation'
import type { AssemblyCoordinates } from '@/types/assembly'

type SearchRequest = { point: AssemblyCoordinates; radiusKm: number; currentLocation: boolean; sequence: number }

export function AssemblyAreasPage() {
  const [search, setSearch] = useState<SearchRequest | null>(null)
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null)
  const [focusRequest, setFocusRequest] = useState(0)
  const sequence = useRef(0)
  const locationRadius = useRef(5)
  const startSearch = (point: AssemblyCoordinates, radiusKm: number, currentLocation: boolean) => {
    setSelectedAreaId(null)
    setSearch({ point, radiusKm, currentLocation, sequence: ++sequence.current })
  }
  const location = useAssemblyLocation(point => startSearch(point, locationRadius.current, true))
  const load = useCallback((signal: AbortSignal) => {
    if (!search) return Promise.reject(new Error('No search'))
    return getNearbyAssemblyAreas(search.point, search.radiusKm, signal)
  }, [search])
  // Request key contains no coordinates and is never persisted.
  const result = useApiResource(search ? String(search.sequence) : null, load)
  const areas = result.status === 'success' ? result.data.areas : []
  const selectArea = useCallback((id: string) => {
    setSelectedAreaId(id)
    setFocusRequest(value => value + 1)
  }, [])
  function resetSearch() {
    location.cancel()
    setSearch(null)
    setSelectedAreaId(null)
  }
  return (
    <div className="mx-auto w-full max-w-7xl space-y-5 sm:space-y-6">
      <header className="rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-8">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Toplanma Alanları</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary sm:text-base">OpenStreetMap topluluğunun işaretlediği acil durum toplanma noktalarını inceleyin.</p>
        <p className="mt-3 text-sm leading-6 text-text-secondary">Bu kayıtlar resmî AFAD toplanma alanları değildir. Veriler eksik veya yalnızca bir tesise ait olabilir; güncel erişim, yapı güvenliği ve güvenli güzergâh garantisi vermez.</p>
      </header>
      <div className="grid items-stretch gap-5 sm:gap-6 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_360px]">
        <AssemblyAreaMap areas={areas} userLocation={search?.point ?? null} selectedAreaId={selectedAreaId} focusRequest={focusRequest} onSelect={selectArea} />
        <AssemblyAreaSearchPanel locationStatus={location.status} loading={result.status === 'loading'} onEdit={resetSearch}
          onLocate={radiusKm => { resetSearch(); locationRadius.current = radiusKm; location.request() }}
          onSearch={(point, radiusKm) => { resetSearch(); startSearch(point, radiusKm, false) }} />
      </div>
      {result.status === 'idle' ? <p role="status" className="rounded-xl border border-border-subtle bg-card p-5 text-sm">Yakındaki noktaları görmek için bir konumla arama yapın.</p> : null}
      {result.status === 'loading' ? <p role="status" className="rounded-xl border border-border-subtle bg-card p-5 text-sm">Toplanma noktaları alınıyor…</p> : null}
      {result.status === 'error' ? <div role="alert" className="rounded-xl border border-border-subtle bg-card p-5 text-sm">
        <p>Veriler alınırken bir sorun oluştu. Lütfen tekrar deneyin.</p>
        <button type="button" onClick={() => { if (search) startSearch(search.point, search.radiusKm, search.currentLocation) }} className="mt-3 min-h-11 rounded-lg border border-border-subtle px-4">Tekrar Dene</button>
      </div> : null}
      {result.status === 'success' ? <>
        <p className="text-sm text-text-secondary">{search?.radiusKm} km arama yarıçapı · {areas.length} kayıt. Uzaklıklar yürüme mesafesi değildir.</p>
        {result.data.truncated ? <p role="status" className="text-sm">İlk 100 kayıt gösteriliyor. Daha dar bir yarıçapla arayabilirsiniz.</p> : null}
        <AssemblyAreaList areas={areas} search={null} selectedAreaId={selectedAreaId} onSelect={selectArea} />
        <p className="text-xs leading-6 text-text-secondary">{result.data.attribution} · {result.data.license} · Kaynak tarihi: {new Date(result.data.sourceTimestamp).toLocaleDateString('tr-TR', { timeZone: 'UTC' })}.
          {' '}<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" className="underline">Kaynak ve lisans</a></p>
      </> : null}
      <AssemblyAreaSafetyNotice />
    </div>
  )
}
