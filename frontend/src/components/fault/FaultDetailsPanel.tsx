import { Activity, MousePointer2 } from 'lucide-react'
import type { FaultFeature, FaultLineDetail } from '@/types/fault'
import { FaultCities } from './FaultCities'
import { FaultEarthquakeTable } from './FaultEarthquakeTable'

export function FaultDetailsPanel({ fault, detail }: { fault: FaultFeature | null; detail?: FaultLineDetail }) {
  // Avoid displaying a stale response for another selected fault after future API integration.
  const current = detail?.faultId === fault?.id ? detail : undefined
  const pending = !current || current.status === 'backend-pending'
  return (
    <section className="rounded-2xl border border-border-subtle/70 bg-card p-4 shadow-sm sm:p-6" aria-labelledby="fault-details-heading">
      <div className="flex items-center gap-3">
        <span className="rounded-full border border-border-subtle p-2"><Activity size={22} className="text-brand-red" aria-hidden="true" /></span>
        <h2 id="fault-details-heading" className="text-lg font-semibold sm:text-xl">Seçili Fay Hattı Bilgileri</h2>
      </div>
      <div role="status" aria-live="polite" className="mt-3">
        {fault ? <p className="break-words font-semibold">{fault.properties.displayName} <span className="font-normal text-text-secondary">· {fault.id}</span></p>
          : <p className="flex items-start gap-3 rounded-xl bg-surface p-5 text-sm leading-6 text-text-secondary"><MousePointer2 size={20} className="mt-0.5 shrink-0" aria-hidden="true" />Detayları görüntülemek için harita üzerinden bir fay hattı seçin.</p>}
      </div>
      {fault ? <>
        {current?.status === 'development' ? <p className="mt-2 text-sm text-text-secondary">Geliştirme amaçlı örnek detaylar; bilimsel veya doğrulanmış kayıtlar değildir.</p> : null}
        <div className="mt-4 grid divide-y divide-border-subtle overflow-hidden rounded-xl border border-border-subtle lg:grid-cols-[0.85fr_1.15fr] lg:divide-x lg:divide-y-0">
          <FaultCities cities={pending ? [] : current.cities} pending={pending} />
          <FaultEarthquakeTable earthquakes={pending ? [] : current.earthquakes} pending={pending} />
        </div>
      </> : null}
    </section>
  )
}
