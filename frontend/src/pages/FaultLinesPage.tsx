import { useState } from 'react'
import { Info } from 'lucide-react'
import { FaultLinesMap } from '@/components/map/FaultLinesMap'
import { FaultDetailsPanel } from '@/components/fault/FaultDetailsPanel'
import { FAULT_LIMIT, getFaults } from '@/api/faults'
import { useApiResource } from '@/hooks/useApiResource'

export function FaultLinesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const result = useApiResource(`faults:${attempt}`, getFaults)
  const features = result.status === 'success' ? result.data.features : []
  const selected = features.find(feature => feature.id === selectedId) ?? null
  return (
    <div className="space-y-4 sm:space-y-5">
      <section className="rounded-2xl border border-border-subtle/70 bg-card p-3 shadow-sm sm:p-6 lg:p-8" aria-labelledby="fault-map-heading" aria-busy={result.status === 'loading'}>
        <h1 id="fault-map-heading" className="sr-only">Fay Hatları</h1>
        {result.status === 'loading' ? <p role="status" className="rounded-xl bg-surface p-6 text-sm">Fay verileri alınıyor…</p> : null}
        {result.status === 'error' ? <div role="alert" className="rounded-xl bg-surface p-6 text-sm">
          <p>Veriler alınırken bir sorun oluştu.</p>
          <button type="button" onClick={() => { setSelectedId(null); setAttempt(value => value + 1) }} className="mt-3 min-h-11 rounded-lg border border-border-subtle px-4">Tekrar Dene</button>
        </div> : null}
        {result.status === 'success' && !features.length ? <p role="status" className="p-6 text-sm text-text-secondary">Gösterilecek fay segmenti bulunmuyor.</p> : null}
        <FaultLinesMap features={features} selectedId={selected?.id ?? null} onSelect={setSelectedId} />
        <div className="mt-5 flex flex-col gap-4 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-text-secondary">
            <span className="flex items-center gap-2"><span className="h-0.5 w-6 bg-fault-line" aria-hidden="true" />Aktif fay segmenti</span>
            <span className="flex items-center gap-2"><span className="h-1 w-6 bg-map-selection" aria-hidden="true" />Seçili segment</span>
            {result.status === 'success' ? <span>{features.length} segment</span> : null}
          </div>
          <div className="flex min-w-0 flex-col gap-1 sm:w-80">
            <label htmlFor="fault-select" className="text-xs font-medium text-text-secondary">Fay segmenti seçin</label>
            <select id="fault-select" value={selected?.id ?? ''} onChange={event => setSelectedId(event.target.value || null)}
              disabled={!features.length} className="min-h-11 w-full min-w-0 rounded-lg border border-border-subtle bg-card px-3 text-sm text-text-primary">
              <option value="">Haritadan veya listeden seçin</option>
              {features.map(feature => <option key={feature.id} value={feature.id}>{feature.properties.displayName} · {feature.properties.sourceId}</option>)}
            </select>
          </div>
        </div>
        {features.length === FAULT_LIMIT ? <p className="mt-3 text-sm">Görüntülenen kayıtlar gösterim sınırına ulaştı; tüm segmentleri içermeyebilir.</p> : null}
        <p className="mt-4 text-xs leading-5 text-text-secondary">
          Fay verisi: <a href="https://github.com/GEMScienceTools/gem-global-active-faults" target="_blank" rel="noreferrer" className="underline underline-offset-2">GEM Foundation · Styron &amp; Pagani (2020)</a>
          {' · '}<a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer" className="underline underline-offset-2">CC BY-SA 4.0</a>.
          {' '}Türkiye ve yakın çevresi gösterilir; kaynak koordinatları korunmuştur. Resmî MTA fay haritası değildir.
        </p>
        {result.status === 'success' ? <p className="mt-2 text-xs leading-5 text-text-secondary">{result.data.attribution} · {result.data.license}</p> : null}
      </section>
      <FaultDetailsPanel fault={selected} />
      <p className="flex items-start gap-2 px-1 text-xs leading-5 text-text-secondary">
        <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        Bir depremin fay çizgisine yakın olması, o fay üzerinde gerçekleştiğini veya o faydan kaynaklandığını göstermez.
      </p>
    </div>
  )
}
