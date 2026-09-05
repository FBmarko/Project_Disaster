import { Activity, MousePointer2 } from 'lucide-react'
import type { FaultFeature } from '@/types/fault'
import { FaultCities } from './FaultCities'
import { FaultEarthquakeTable } from './FaultEarthquakeTable'

export function FaultDetailsPanel({ fault }: { fault: FaultFeature | null }) {
  return (
    <section className="rounded-2xl border border-border-subtle/70 bg-card p-4 shadow-sm sm:p-6" aria-labelledby="fault-details-heading">
      <div className="flex items-center gap-3">
        <span className="rounded-full border border-border-subtle p-2"><Activity size={22} className="text-brand-red-foreground" aria-hidden="true" /></span>
        <h2 id="fault-details-heading" className="text-lg font-semibold sm:text-xl">Seçili Fay Hattı Bilgileri</h2>
      </div>
      <div role="status" aria-live="polite" className="mt-3">
        {fault ? <p className="break-words font-semibold">{fault.properties.displayName} <span className="font-normal text-text-secondary">· {fault.properties.sourceId}</span></p>
          : <p className="flex items-start gap-3 rounded-xl bg-surface p-5 text-sm leading-6 text-text-secondary"><MousePointer2 size={20} className="mt-0.5 shrink-0" aria-hidden="true" />Detayları görüntülemek için harita üzerinden bir fay hattı seçin.</p>}
      </div>
      {fault ? <>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div><dt className="text-text-secondary">Kaynak sınıflandırması</dt><dd>{fault.properties.faultType ?? 'Belirtilmemiş'}</dd></div>
          <div><dt className="text-text-secondary">Aktivite bilgisi</dt><dd>{fault.properties.activityStatus ?? 'Belirtilmemiş'}</dd></div>
        </dl>
        <div className="mt-4 grid divide-y divide-border-subtle overflow-hidden rounded-xl border border-border-subtle lg:grid-cols-[0.65fr_1.35fr] lg:divide-x lg:divide-y-0">
          <FaultCities cities={[]} pending />
          <FaultEarthquakeTable key={fault.id} faultId={fault.id} />
        </div>
      </> : null}
    </section>
  )
}
