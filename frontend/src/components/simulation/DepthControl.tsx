import { SIMULATION_INPUTS } from '@/constants/simulation'

export function DepthControl({ value, error, onChange }: {
  value: number
  error?: string
  onChange: (value: number) => void
}) {
  return (
    <fieldset aria-describedby={error ? 'simulation-depth-error' : 'simulation-depth-help'}>
      <legend className="font-semibold">Derinlik</legend>
      <div className="mt-3 grid grid-cols-4 gap-1 rounded-xl border border-border-subtle p-1">
        {SIMULATION_INPUTS.depthKm.presets.map((depth) => <label key={depth} className="relative min-w-0 cursor-pointer">
          <input type="radio" name="simulation-depth" value={depth} checked={value === depth}
            onChange={() => onChange(depth)} aria-invalid={Boolean(error)} className="peer sr-only" />
          <span className="flex min-h-11 items-center justify-center rounded-lg px-1 text-sm tabular-nums peer-checked:bg-brand-red peer-checked:font-semibold peer-checked:text-white peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-red peer-disabled:cursor-not-allowed">{depth} km</span>
        </label>)}
      </div>
      <p id="simulation-depth-help" className="mt-2 text-xs leading-5 text-text-secondary">Deprem odağının yüzeyden derinliği.</p>
      {error ? <p id="simulation-depth-error" className="mt-2 text-xs text-red-700">{error}</p> : null}
    </fieldset>
  )
}
