import type { AssemblyArea, AssemblyAreaSearch } from '@/types/assembly'
import { AssemblyAreaCard } from './AssemblyAreaCard'
import { AssemblyAreaEmptyState } from './AssemblyAreaEmptyState'

export function AssemblyAreaList({ areas, search, selectedAreaId, onSelect }: {
  areas: readonly AssemblyArea[]
  search: AssemblyAreaSearch | null
  selectedAreaId: string | null
  onSelect: (id: string) => void
}) {
  const selectedArea = areas.find((area) => area.id === selectedAreaId)
  return (
    <section aria-labelledby="assembly-results-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-7">
      <h2 id="assembly-results-heading" className="text-xl font-semibold">{search?.mode === 'REGION' ? 'Toplanma Alanları' : 'Yakındaki Toplanma Alanları'}</h2>
      {search?.mode === 'REGION' ? <p className="mt-2 text-sm leading-6 wrap-anywhere text-text-secondary">
        Seçilen bölge: {[search.province, search.district, search.neighborhood].filter(Boolean).join(' / ')}
      </p> : null}
      <p role="status" aria-live="polite" aria-atomic="true" className="mt-2 text-sm leading-6">{selectedArea ? `Seçili alan: ${selectedArea.name}` : ''}</p>
      <div className="mt-5">
        {areas.length ? <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {areas.map((area) => <li key={area.id} className="min-w-0"><AssemblyAreaCard area={area} selected={area.id === selectedAreaId} onSelect={onSelect} /></li>)}
        </ul> : <AssemblyAreaEmptyState search={search} />}
      </div>
    </section>
  )
}
