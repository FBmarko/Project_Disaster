import { useReducer } from 'react'
import { SimulationMap } from '@/components/simulation/SimulationMap'
import { SimulationSettingsPanel } from '@/components/simulation/SimulationSettingsPanel'
import { createSimulationSetup, selectedSimulationLocation, simulationSetupReducer } from '@/utils/simulationDraft'

export function SimulationPage() {
  const [state, dispatch] = useReducer(simulationSetupReducer, undefined, createSimulationSetup)
  return (
    <div className="rounded-2xl border border-border-subtle/70 bg-card p-3 shadow-sm sm:p-4">
      <h1 className="sr-only">Deprem Simülasyonu</h1>
      <div className="grid items-stretch gap-4 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_400px]">
        <SimulationMap location={selectedSimulationLocation(state.draft)}
          onSelect={(location) => dispatch({ type: 'select-location', location })} />
        <SimulationSettingsPanel state={state} onAction={dispatch} />
      </div>
    </div>
  )
}
