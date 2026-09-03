import { useState } from 'react'
import { Info } from 'lucide-react'
import { FaultLinesMap } from '@/components/map/FaultLinesMap'
import { FaultDetailsPanel } from '@/components/fault/FaultDetailsPanel'
import { loadTurkeyFaults } from '@/data/turkeyFaults'

const data = loadTurkeyFaults()

export function FaultLinesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = data.features.find((feature) => feature.id === selectedId) ?? null
  return (
    <div className="space-y-4 sm:space-y-5">
      <section className="rounded-2xl border border-border-subtle/70 bg-card p-3 shadow-sm sm:p-6 lg:p-8" aria-labelledby="fault-map-heading">
        <h1 id="fault-map-heading" className="sr-only">Fay Hatları</h1>
        {data.status === 'error' ? <p role="alert" className="rounded-xl bg-surface p-6 text-sm">Fay verisi yüklenemedi. Lütfen sayfayı yenileyin.</p>
          : data.features.length === 0 ? <p className="p-6 text-sm text-text-secondary">Gösterilecek fay segmenti bulunmuyor.</p>
            : <FaultLinesMap features={data.features} selectedId={selectedId} onSelect={setSelectedId} />}
        <div className="mt-5 flex flex-col gap-4 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-text-secondary">
            <span className="flex items-center gap-2"><span className="h-0.5 w-6 bg-brand-red" aria-hidden="true" />Aktif fay segmenti</span>
            <span className="flex items-center gap-2"><span className="h-1 w-6 bg-red-700" aria-hidden="true" />Seçili segment</span>
            <span>{data.features.length} segment</span>
          </div>
          <div className="flex min-w-0 flex-col gap-1 sm:w-80">
            <label htmlFor="fault-select" className="text-xs font-medium text-text-secondary">Fay segmenti seçin</label>
            <select id="fault-select" value={selectedId ?? ''} onChange={(event) => setSelectedId(event.target.value || null)}
              disabled={data.status === 'error'} className="min-h-11 w-full min-w-0 rounded-lg border border-border-subtle bg-white px-3 text-sm">
              <option value="">Haritadan veya listeden seçin</option>
              {data.features.map((feature) => <option key={feature.id} value={feature.id}>{feature.properties.displayName} · {feature.id}</option>)}
            </select>
          </div>
        </div>
        <p className="mt-4 text-xs leading-5 text-text-secondary">
          Fay verisi: <a href="https://github.com/GEMScienceTools/gem-global-active-faults" target="_blank" rel="noreferrer" className="underline underline-offset-2">GEM Foundation · Styron &amp; Pagani (2020)</a>
          {' · '}<a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer" className="underline underline-offset-2">CC BY-SA 4.0</a>.
          {' '}Türkiye görünümü için filtrelenmiştir; kaynak koordinatları korunmuştur. Kaynakta adı bulunmayan segmentler kimlikleriyle gösterilir.
        </p>
      </section>
      <FaultDetailsPanel fault={selected} />
      <p className="flex items-start gap-2 px-1 text-xs leading-5 text-text-secondary">
        <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        Fay geometrileri açık coğrafi kaynaktan alınan gerçek verilerdir. Şehir ve geçmiş deprem detayları backend entegrasyonunu beklemektedir; henüz kayıt gösterilmemektedir.
      </p>
    </div>
  )
}
