import { lazy, Suspense } from 'react'
import { MousePointer2 } from 'lucide-react'
import type { SimulationLocation } from '@/types/simulation'
import { SimulationMapState } from './SimulationMapState'
import { SimulationMapBoundary } from './SimulationMapBoundary'

// Keep the Google wrapper out of other pages and avoid loading it without a key.
const GoogleSimulationMap = lazy(() => import('./GoogleSimulationMap'))

export function SimulationMap({ location, onSelect }: {
  location: SimulationLocation | null
  onSelect: (location: SimulationLocation) => void
}) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim()
  return (
    <section aria-label="Simülasyon konumu haritası" aria-describedby="simulation-map-help"
      className="flex min-w-0 flex-col overflow-hidden rounded-2xl border border-border-subtle bg-card">
      <div className="relative h-[360px] sm:h-[480px] lg:h-auto lg:min-h-[600px] lg:flex-1">
        {apiKey ? <SimulationMapBoundary><Suspense fallback={<SimulationMapState state="loading" />}>
          <GoogleSimulationMap apiKey={apiKey} location={location} onSelect={onSelect} />
        </Suspense></SimulationMapBoundary> : <SimulationMapState state="missing-key" />}
      </div>
      <p id="simulation-map-help" className="flex items-start gap-2 border-t border-border-subtle px-4 py-3 text-xs leading-5 text-text-secondary">
        <MousePointer2 size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
        Haritada bir noktaya tıklayarak veya dokunarak konum seçin. Başka bir noktayı seçtiğinizde işaretçi taşınır.
      </p>
    </section>
  )
}
