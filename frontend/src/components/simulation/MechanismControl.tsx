import { FAULT_MECHANISMS } from '@/constants/simulation'
import type { FaultMechanism } from '@/types/simulation'

export function MechanismControl({
  value,
  error,
  onChange,
}: {
  value: FaultMechanism | null
  error?: string
  onChange: (value: FaultMechanism) => void
}) {
  return (
    <fieldset aria-describedby={error ? 'simulation-mechanism-error' : 'simulation-mechanism-help'}>
      <legend className="font-semibold">Fay Mekanizması</legend>
      <div className="mt-3 space-y-2">
        {FAULT_MECHANISMS.map((mech) => {
          const isSelected = value === mech.value
          return (
            <label
              key={mech.value}
              className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors ${
                isSelected
                  ? 'border-brand-red bg-brand-red-soft/30 font-medium'
                  : 'border-border-subtle hover:border-border hover:bg-surface/50'
              }`}
            >
              <input
                type="radio"
                name="simulation-mechanism"
                value={mech.value}
                checked={isSelected}
                onChange={() => onChange(mech.value)}
                aria-invalid={Boolean(error)}
                className="mt-1 h-4 w-4 accent-brand-red"
              />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-text-primary">{mech.label}</div>
                <div className="text-xs text-text-secondary">{mech.description}</div>
              </div>
            </label>
          )
        })}
      </div>
      <p id="simulation-mechanism-help" className="mt-2 text-xs leading-5 text-text-secondary">
        Akkar et al. (2014) yer hareketi azalım modeli için fay türü seçimi zorunludur.
      </p>
      {error ? (
        <p id="simulation-mechanism-error" className="mt-2 text-xs text-error">
          {error}
        </p>
      ) : null}
    </fieldset>
  )
}
