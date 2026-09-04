import { useState } from 'react'
import { AssemblyAreaMap } from '@/components/assembly/AssemblyAreaMap'
import { AssemblyAreaSearchPanel } from '@/components/assembly/AssemblyAreaSearchPanel'
import { AssemblyAreaList } from '@/components/assembly/AssemblyAreaList'
import { AssemblyAreaSafetyNotice } from '@/components/assembly/AssemblyAreaSafetyNotice'
import { ASSEMBLY_AREAS } from '@/constants/assembly'
import { useAssemblyLocation } from '@/hooks/useAssemblyLocation'
import type { AssemblyAreaSearch } from '@/types/assembly'
import { hasValidAssemblyCoordinates } from '@/utils/assemblyAreas'

export function AssemblyAreasPage() {
  const [search, setSearch] = useState<AssemblyAreaSearch | null>(null)
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null)
  const [focusRequest, setFocusRequest] = useState(0)
  const location = useAssemblyLocation((point) => setSearch({ mode: 'CURRENT_LOCATION', ...point }))

  function resetSearch() {
    location.cancel()
    setSearch(null)
    setSelectedAreaId(null)
  }
  function selectArea(id: string) {
    const area = ASSEMBLY_AREAS.find((candidate) => candidate.id === id)
    if (!hasValidAssemblyCoordinates(area)) return
    setSelectedAreaId(id)
    setFocusRequest((value) => value + 1)
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5 sm:space-y-6">
      <header className="rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-8">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Toplanma Alanları</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary sm:text-base">
          Bulunduğunuz bölgedeki afet toplanma alanlarını harita üzerinden inceleyin ve ihtiyaç anında ulaşabileceğiniz noktaları önceden tanıyın.
        </p>
      </header>
      <div className="grid items-stretch gap-5 sm:gap-6 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_360px]">
        <AssemblyAreaMap areas={ASSEMBLY_AREAS} userLocation={search?.mode === 'CURRENT_LOCATION' ? search : null}
          selectedAreaId={selectedAreaId} focusRequest={focusRequest} onSelect={selectArea} />
        <AssemblyAreaSearchPanel locationStatus={location.status} onEdit={resetSearch}
          onLocate={() => { resetSearch(); location.request() }}
          onSearch={(region) => { resetSearch(); setSearch(region) }} />
      </div>
      <AssemblyAreaList areas={ASSEMBLY_AREAS} search={search} selectedAreaId={selectedAreaId} onSelect={selectArea} />
      <AssemblyAreaSafetyNotice />
    </div>
  )
}
