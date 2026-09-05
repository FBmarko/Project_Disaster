import type { HouseholdChoice } from '@/types/preparedness'

export function BooleanChoice({ name, label, value, error, onChange }: {
  name: HouseholdChoice
  label: string
  value: boolean | null
  error?: string
  onChange: (value: boolean) => void
}) {
  const errorId = `preparedness-${name}-error`
  return (
    <fieldset className="min-w-0" aria-describedby={error ? errorId : undefined}>
      <legend className="mb-2 text-sm font-medium">{label}</legend>
      <div className="grid grid-cols-2 gap-2">
        {[{ value: true, label: 'Evet' }, { value: false, label: 'Hayır' }].map((option) => (
          <label key={option.label} className="relative cursor-pointer">
            <input type="radio" name={name} value={String(option.value)} required
              checked={value === option.value} onChange={() => onChange(option.value)}
              aria-invalid={Boolean(error)} aria-describedby={error ? errorId : undefined}
              className="peer sr-only" />
            <span className="flex min-h-12 items-center justify-center rounded-xl border border-border-subtle bg-card px-3 py-2 text-sm font-medium text-text-secondary peer-checked:border-brand-red peer-checked:bg-brand-red-soft peer-checked:text-text-primary peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-brand-red hover:bg-surface">
              {option.label}
            </span>
          </label>
        ))}
      </div>
      {error ? <p id={errorId} className="mt-2 text-sm text-error">{error}</p> : null}
    </fieldset>
  )
}
