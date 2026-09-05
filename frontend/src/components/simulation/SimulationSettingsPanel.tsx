import { Activity, Info, Play } from 'lucide-react'
import { SIMULATION_UNAVAILABLE_MESSAGE } from '@/constants/simulation'
import type { SimulationAction, SimulationSetupState } from '@/types/simulation'
import { prepareSimulationRequest, selectedSimulationLocation, validateSimulationDraft } from '@/utils/simulationDraft'
import { DepthControl } from './DepthControl'
import { ImpactRadiusControl } from './ImpactRadiusControl'
import { LocationSummary } from './LocationSummary'
import { MagnitudeControl } from './MagnitudeControl'

export function SimulationSettingsPanel({ state, onAction }: {
  state: SimulationSetupState
  onAction: (action: SimulationAction) => void
}) {
  const { draft } = state
  const location = selectedSimulationLocation(draft)
  const errors = validateSimulationDraft(draft)
  const valid = Object.keys(errors).length === 0

  return (
    <section aria-labelledby="simulation-settings-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-6">
      <h2 id="simulation-settings-heading" className="flex items-center gap-3 text-xl font-semibold">
        <Activity size={28} aria-hidden="true" className="shrink-0 text-brand-red-foreground" />Simülasyon Ayarları
      </h2>
      <form noValidate className="mt-6 space-y-6" onSubmit={(event) => {
        event.preventDefault()
        // The typed payload is only prepared/validated. There is no transport or result.
        if (prepareSimulationRequest(draft).ok) onAction({ type: 'submit' })
      }}>
        <LocationSummary location={location} onClear={() => onAction({ type: 'clear-location' })} />
        <fieldset disabled={!location} className="min-w-0 space-y-6 disabled:opacity-60">
          <legend className="sr-only">Deprem senaryosu girdileri</legend>
          <MagnitudeControl value={draft.magnitude} error={errors.magnitude}
            onChange={(value) => onAction({ type: 'set-parameter', field: 'magnitude', value })} />
          <DepthControl value={draft.depthKm} error={errors.depthKm}
            onChange={(value) => onAction({ type: 'set-parameter', field: 'depthKm', value })} />
          <ImpactRadiusControl value={draft.radiusKm} error={errors.radiusKm}
            onChange={(value) => onAction({ type: 'set-parameter', field: 'radiusKm', value })} />
        </fieldset>
        <div>
          <button type="submit" disabled={!valid} aria-describedby="simulation-service-notice"
            className="inline-flex min-h-14 w-full items-center justify-center gap-3 rounded-xl bg-brand-red px-4 py-3 font-semibold text-white transition-colors hover:bg-brand-red-hover disabled:cursor-not-allowed disabled:opacity-45">
            <Play size={18} fill="currentColor" aria-hidden="true" />Senaryoyu Hazırla
          </button>
          <div role="status" aria-live="polite" aria-atomic="true">
            {state.status === 'backend-pending' ? <p className="mt-3 rounded-xl border border-border-subtle bg-surface p-3 text-sm leading-6">{SIMULATION_UNAVAILABLE_MESSAGE}</p> : null}
          </div>
          <p id="simulation-service-notice" className="mt-3 flex items-start gap-2 text-xs leading-5 text-text-secondary">
            <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            Bu ekran senaryo hazırlığı içindir. Girdi seçenekleri geliştirme amaçlıdır; henüz simülasyon veya hasar hesabı yapılmaz.
          </p>
        </div>
      </form>
    </section>
  )
}
