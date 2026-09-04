import { Check, ExternalLink, MapPin } from 'lucide-react'
import type { AssemblyArea } from '@/types/assembly'
import { assemblyDirectionsUrl } from '@/utils/assemblyAreas'

export function AssemblyAreaCard({ area, selected, onSelect }: {
  area: AssemblyArea
  selected: boolean
  onSelect: (id: string) => void
}) {
  const directions = assemblyDirectionsUrl(area)
  return (
    <article aria-label={area.name} className={`min-w-0 rounded-xl border p-5 wrap-anywhere ${selected ? 'border-brand-red bg-brand-red-soft' : 'border-border-subtle bg-card'}`}>
      {selected ? <p className="mb-2 flex items-center gap-2 text-sm font-semibold"><Check size={18} aria-hidden="true" />Seçili alan</p> : null}
      <h3 className="text-lg font-semibold">{area.name}</h3>
      <p className="mt-2 text-sm leading-6 text-text-secondary">{[area.province, area.district].filter(Boolean).join(' / ')}</p>
      {area.neighborhood?.trim() ? <p className="mt-1 text-sm leading-6 text-text-secondary">{area.neighborhood}</p> : null}
      {area.address?.trim() ? <p className="mt-2 text-sm leading-6">{area.address}</p> : null}
      {directions ? <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={() => onSelect(area.id)} aria-pressed={selected}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border-subtle bg-card px-3 py-2 text-sm font-medium hover:bg-surface">
          <MapPin size={17} aria-hidden="true" />Haritada Göster
        </button>
        <a href={directions} target="_blank" rel="noopener noreferrer"
          aria-label={`${area.name} için Yol Tarifi (yeni sekmede açılır)`}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border-subtle bg-card px-3 py-2 text-sm font-medium hover:bg-surface">
          Yol Tarifi<ExternalLink size={16} aria-hidden="true" />
        </a>
      </div> : null}
    </article>
  )
}
