import { SIMULATION_INPUTS } from '@/constants/simulation'

export function ImpactRadiusControl({ value, error, onChange }: {
  value: number
  error?: string
  onChange: (value: number) => void
}) {
  return (
    <fieldset aria-describedby={error ? 'simulation-radius-error' : 'simulation-radius-help'}>
      <legend className="font-semibold">Etki Alanı</legend>
      <div className="mt-3 grid grid-cols-2 gap-1 rounded-xl border border-border-subtle p-1 min-[380px]:grid-cols-4">
        {SIMULATION_INPUTS.radiusKm.options.map((radius) => <label key={radius} className="relative min-w-0 cursor-pointer">
          <input type="radio" name="simulation-radius" value={radius} checked={value === radius}
            onChange={() => onChange(radius)} aria-invalid={Boolean(error)} className="peer sr-only" />
          <span className="flex min-h-11 items-center justify-center rounded-lg px-1 text-sm tabular-nums peer-checked:bg-brand-red peer-checked:font-semibold peer-checked:text-white peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-red peer-disabled:cursor-not-allowed">{radius} km</span>
        </label>)}
      </div>
      <p id="simulation-radius-help" className="mt-2 text-xs leading-5 text-text-secondary">İncelenmesi istenen yarıçap; hesaplanmış hasar alanı değildir.</p>
      {error ? <p id="simulation-radius-error" className="mt-2 text-xs text-error">{error}</p> : null}
    </fieldset>
  )
}
