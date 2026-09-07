import { Activity, Info, Layers, Play } from 'lucide-react'
import { calculateScenario } from '@/api/scenario'
import { SCENARIO_VS30_LABEL } from '@/constants/simulation'
import type { SimulationAction, SimulationSetupState } from '@/types/simulation'
import { prepareSimulationRequest, selectedSimulationLocation, validateSimulationDraft } from '@/utils/simulationDraft'
import { DepthControl } from './DepthControl'
import { ImpactRadiusControl } from './ImpactRadiusControl'
import { LocationSummary } from './LocationSummary'
import { MagnitudeControl } from './MagnitudeControl'
import { MechanismControl } from './MechanismControl'
import { ScenarioResultView } from './ScenarioResultView'

export function SimulationSettingsPanel({
  state,
  onAction,
}: {
  state: SimulationSetupState
  onAction: (action: SimulationAction) => void
}) {
  const { draft } = state
  const location = selectedSimulationLocation(draft)
  const errors = validateSimulationDraft(draft)
  const valid = Object.keys(errors).length === 0

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const req = prepareSimulationRequest(draft)
    if (!req.ok) return

    onAction({ type: 'start-submit' })
    try {
      const result = await calculateScenario(req.payload)
      onAction({ type: 'calculation-success', result })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Senaryo hesaplaması sırasında bir hata oluştu.'
      onAction({ type: 'calculation-error', error: message })
    }
  }

  return (
    <section aria-labelledby="simulation-settings-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-6">
      <h2 id="simulation-settings-heading" className="flex items-center gap-3 text-xl font-semibold text-text-primary">
        <Activity size={28} aria-hidden="true" className="shrink-0 text-brand-red-foreground" />
        Simülasyon Ayarları
      </h2>
      <form noValidate className="mt-6 space-y-6" onSubmit={handleSubmit}>
        <LocationSummary location={location} onClear={() => onAction({ type: 'clear-location' })} />
        <fieldset disabled={!location} className="min-w-0 space-y-6 disabled:opacity-60">
          <legend className="sr-only">Deprem senaryosu girdileri</legend>
          <MagnitudeControl
            value={draft.magnitude}
            error={errors.magnitude}
            onChange={(value) => onAction({ type: 'set-parameter', field: 'magnitude', value })}
          />
          <DepthControl
            value={draft.depthKm}
            error={errors.depthKm}
            onChange={(value) => onAction({ type: 'set-parameter', field: 'depthKm', value })}
          />
          <MechanismControl
            value={draft.mechanism}
            error={errors.mechanism}
            onChange={(mechanism) => onAction({ type: 'set-mechanism', mechanism })}
          />
          <ImpactRadiusControl
            value={draft.radiusKm}
            error={errors.radiusKm}
            onChange={(value) => onAction({ type: 'set-parameter', field: 'radiusKm', value })}
          />
          <div className="flex items-center gap-2 rounded-xl border border-border-subtle bg-surface/50 p-3 text-xs text-text-secondary">
            <Layers size={16} aria-hidden="true" className="shrink-0 text-blue-600 dark:text-blue-400" />
            <span>{SCENARIO_VS30_LABEL}</span>
          </div>
        </fieldset>
        <div>
          <button
            type="submit"
            disabled={!valid || state.status === 'loading'}
            aria-describedby="simulation-service-notice"
            className="inline-flex min-h-14 w-full items-center justify-center gap-3 rounded-xl bg-brand-red px-4 py-3 font-semibold text-white transition-colors hover:bg-brand-red-hover disabled:cursor-not-allowed disabled:opacity-45"
          >
            <Play size={18} fill="currentColor" aria-hidden="true" />
            {state.status === 'loading' ? 'Hesaplanıyor...' : 'Senaryoyu Hesapla'}
          </button>
          <div role="status" aria-live="polite" aria-atomic="true">
            {state.status === 'error' && state.error ? (
              <p className="mt-3 rounded-xl border border-error/20 bg-error/10 p-3 text-sm text-error">
                {state.error}
              </p>
            ) : null}
          </div>
          <p id="simulation-service-notice" className="mt-3 flex items-start gap-2 text-xs leading-5 text-text-secondary">
            <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            Akkar et al. (2014) azalım modeli ile deterministik senaryo PGA hesaplanır. Resmi tahmin veya bina hasar analizi değildir.
          </p>
        </div>
      </form>

      {state.status === 'success' && state.result ? (
        <ScenarioResultView result={state.result} />
      ) : null}
    </section>
  )
}
