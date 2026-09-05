import { ArrowRight, UsersRound } from 'lucide-react'
import { DISASTER_TYPES, HOUSEHOLD_CHOICES, HOUSEHOLD_SIZE } from '@/constants/preparedness'
import { TURKEY_PROVINCES } from '@/constants/provinces'
import type { PreparednessAction, PreparednessDraft, PreparednessState } from '@/types/preparedness'
import { validatePreparednessDraft } from '@/utils/preparednessDraft'
import { BooleanChoice } from './BooleanChoice'

const controlClass = 'min-h-12 w-full min-w-0 rounded-xl border border-border-subtle bg-card px-3 py-2 text-sm text-text-primary aria-invalid:border-error'
const labelClass = 'mb-2 block text-sm font-medium'
const errorClass = 'mt-2 text-sm text-error'

export function PreparednessForm({ state, onAction }: {
  state: PreparednessState
  onAction: (action: PreparednessAction) => void
}) {
  const { draft } = state
  const errors = state.submitted ? validatePreparednessDraft(draft) : {}
  function change<K extends keyof PreparednessDraft>(field: K, value: PreparednessDraft[K]) {
    onAction({ type: 'change', draft: { ...draft, [field]: value } })
  }

  return (
    <section aria-labelledby="preparedness-form-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-7">
      <h2 id="preparedness-form-heading" className="flex items-center gap-3 text-xl font-semibold">
        <UsersRound size={23} aria-hidden="true" className="shrink-0 text-brand-red-foreground" />
        Evinizi tanıyalım
      </h2>
      <p className="mt-2 text-sm leading-6 text-text-secondary">Hazırlık ihtiyaçlarınızı belirlemek için tüm alanları doldurun.</p>

      <form noValidate className="mt-6 space-y-5" onSubmit={(event) => {
        event.preventDefault()
        const invalidField = Object.keys(validatePreparednessDraft(draft))[0]
        onAction({ type: 'submit' })
        if (invalidField) event.currentTarget.querySelector<HTMLElement>(`[name="${invalidField}"]`)?.focus()
      }}>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <div className="min-w-0">
            <label htmlFor="preparedness-city" className={labelClass}>Şehir</label>
            <select id="preparedness-city" name="city" required value={draft.city}
              onChange={(event) => change('city', event.target.value)} className={controlClass}
              aria-invalid={Boolean(errors.city)} aria-describedby={errors.city ? 'preparedness-city-error' : undefined}>
              <option value="">Şehir seçin</option>
              {TURKEY_PROVINCES.map((city) => <option key={city} value={city}>{city}</option>)}
            </select>
            {errors.city ? <p id="preparedness-city-error" className={errorClass}>{errors.city}</p> : null}
          </div>
          <div className="min-w-0">
            <label htmlFor="preparedness-disaster" className={labelClass}>Afet Türü</label>
            <select id="preparedness-disaster" name="disasterType" required value={draft.disasterType}
              onChange={(event) => change('disasterType', event.target.value)} className={controlClass}
              aria-invalid={Boolean(errors.disasterType)} aria-describedby={errors.disasterType ? 'preparedness-disaster-error' : undefined}>
              {DISASTER_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
            {errors.disasterType ? <p id="preparedness-disaster-error" className={errorClass}>{errors.disasterType}</p> : null}
          </div>
        </div>

        <div>
          <label htmlFor="preparedness-household" className={labelClass}>Evdeki Kişi Sayısı</label>
          <input id="preparedness-household" name="householdSize" type="number" inputMode="numeric" required
            min={HOUSEHOLD_SIZE.min} max={HOUSEHOLD_SIZE.max} step={1} value={draft.householdSize ?? ''}
            onChange={(event) => change('householdSize', Number.isNaN(event.target.valueAsNumber) ? null : event.target.valueAsNumber)}
            className={controlClass} aria-invalid={Boolean(errors.householdSize)}
            aria-describedby={`preparedness-household-hint${errors.householdSize ? ' preparedness-household-error' : ''}`} />
          <p id="preparedness-household-hint" className="mt-2 text-xs leading-5 text-text-secondary">Kendiniz dahil, 1–20 kişi arasında belirtin.</p>
          {errors.householdSize ? <p id="preparedness-household-error" className={errorClass}>{errors.householdSize}</p> : null}
        </div>

        <div className="space-y-5 border-t border-border-subtle pt-5">
          {HOUSEHOLD_CHOICES.map(({ name, label }) => (
            <BooleanChoice key={name} name={name} label={label} value={draft[name]}
              error={errors[name]} onChange={(value) => change(name, value)} />
          ))}
        </div>

        {Object.keys(errors).length ? <p role="alert" className={errorClass}>Lütfen işaretli alanları kontrol edin.</p> : null}
        <div>
          <button type="submit" aria-describedby="preparedness-availability"
            className="flex min-h-14 w-full items-center justify-center gap-3 rounded-xl bg-brand-red px-4 py-3 text-[19px] font-bold text-white hover:bg-brand-red-hover">
            Rehberimi Oluştur <ArrowRight size={18} aria-hidden="true" className="shrink-0" />
          </button>
          <p id="preparedness-availability" className="mt-3 text-xs leading-5 text-text-secondary">
            Kişisel rehber oluşturma şu anda kullanılamıyor. Bilgilerinizi bu sayfada hazırlayabilirsiniz.
          </p>
          <div role="status" aria-live="polite" aria-atomic="true">
            {state.preparedProfile ? <p className="mt-3 rounded-xl border border-border-subtle bg-surface p-3 text-sm leading-6">
              Bilgileriniz hazır. Henüz bir rehber oluşturulmadı. Bilgileriniz yalnızca bu sayfa açıkken korunur.
            </p> : null}
          </div>
        </div>
      </form>
    </section>
  )
}
