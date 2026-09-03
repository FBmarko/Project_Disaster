import { MapPin, X } from 'lucide-react'
import type { SimulationLocation } from '@/types/simulation'

export function LocationSummary({ location, onClear }: {
  location: SimulationLocation | null
  onClear: () => void
}) {
  return (
    <section aria-labelledby="simulation-location-heading">
      <h3 id="simulation-location-heading" className="font-semibold">Seçilen Konum</h3>
      <div className="mt-3 rounded-xl border border-border-subtle bg-surface/50 p-4">
        <div className="flex items-start gap-3">
          <MapPin size={21} aria-hidden="true" className="mt-0.5 shrink-0 text-brand-red" />
          <div aria-live="polite" aria-atomic="true" className="min-w-0 flex-1">
            {location ? <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm tabular-nums">
              <dt className="text-text-secondary">Enlem</dt><dd>{location.latitude.toFixed(4)}°</dd>
              <dt className="text-text-secondary">Boylam</dt><dd>{location.longitude.toFixed(4)}°</dd>
            </dl> : <p className="text-sm leading-6 text-text-secondary">Simülasyon ayarlarını yapılandırmak için harita üzerinden bir konum seçin.</p>}
          </div>
        </div>
        {location ? <button type="button" onClick={onClear}
          className="mt-3 inline-flex min-h-10 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-text-secondary hover:bg-white hover:text-brand-red">
          <X size={15} aria-hidden="true" />Konumu Temizle
        </button> : null}
      </div>
    </section>
  )
}
