import { Component, lazy, Suspense, type ReactNode } from 'react'
import { LocateFixed, MapPin } from 'lucide-react'
import type { AssemblyArea, AssemblyCoordinates } from '@/types/assembly'
import { AssemblyAreaMapState } from './AssemblyAreaMapState'

const GoogleAssemblyAreaMap = lazy(() => import('./GoogleAssemblyAreaMap'))

export interface AssemblyMapProps {
  areas: readonly AssemblyArea[]
  userLocation: AssemblyCoordinates | null
  selectedAreaId: string | null
  focusRequest: number
  onSelect: (id: string) => void
}

/** Matches the simulation map's isolated loading/error boundary without changing its behavior. */
class AssemblyMapBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <AssemblyAreaMapState state="error" /> : this.props.children }
}

export function AssemblyAreaMap(props: AssemblyMapProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim()
  return (
    <section aria-label="Toplanma alanları haritası" className="flex min-w-0 flex-col overflow-hidden rounded-2xl border border-border-subtle bg-card shadow-sm">
      <div className="relative h-[340px] sm:h-[460px] lg:h-auto lg:min-h-[600px] lg:flex-1">
        {apiKey ? <AssemblyMapBoundary><Suspense fallback={<AssemblyAreaMapState state="loading" />}>
          <GoogleAssemblyAreaMap {...props} apiKey={apiKey} />
        </Suspense></AssemblyMapBoundary> : <AssemblyAreaMapState state="missing-key" />}
      </div>
      <div aria-label="Harita işaretleri" className="flex flex-wrap gap-x-5 gap-y-2 border-t border-border-subtle px-4 py-3 text-xs leading-5 text-text-secondary">
        <span className="flex items-center gap-2"><LocateFixed size={16} aria-hidden="true" className="text-blue-700" />Kullanıcı Konumu</span>
        <span className="flex items-center gap-2"><MapPin size={16} aria-hidden="true" className="text-brand-red-foreground" />Toplanma Alanı</span>
      </div>
    </section>
  )
}
