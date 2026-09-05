import { SIMULATION_INPUTS } from '@/constants/simulation'

export function MagnitudeControl({ value, error, onChange }: {
  value: number
  error?: string
  onChange: (value: number) => void
}) {
  const config = SIMULATION_INPUTS.magnitude
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor="simulation-magnitude" className="font-semibold">Deprem Büyüklüğü</label>
        <output htmlFor="simulation-magnitude" className="rounded-lg bg-brand-red-soft px-2.5 py-1 text-sm font-semibold tabular-nums text-brand-red-foreground">{value.toFixed(1)} Mw</output>
      </div>
      <input id="simulation-magnitude" type="range" min={config.min} max={config.max} step={config.step}
        value={value} onChange={(event) => onChange(event.currentTarget.valueAsNumber)}
        aria-valuetext={`${value.toFixed(1)} Mw`} aria-invalid={Boolean(error)}
        aria-describedby={error ? 'simulation-magnitude-error' : 'simulation-magnitude-help'}
        className="mt-2 h-11 w-full cursor-pointer accent-brand-red disabled:cursor-not-allowed" />
      <div className="flex justify-between text-xs tabular-nums text-text-secondary" aria-hidden="true"><span>{config.min.toFixed(1)} Mw</span><span>{config.max.toFixed(1)} Mw</span></div>
      <p id="simulation-magnitude-help" className="mt-2 text-xs leading-5 text-text-secondary">Senaryo için belirlediğiniz moment büyüklüğü.</p>
      {error ? <p id="simulation-magnitude-error" className="mt-2 text-xs text-error">{error}</p> : null}
    </div>
  )
}
