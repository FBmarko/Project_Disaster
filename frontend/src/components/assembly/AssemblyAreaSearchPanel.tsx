import { useState } from 'react'
import { LocateFixed, Search } from 'lucide-react'
import { TURKEY_PROVINCES } from '@/constants/provinces'
import { ASSEMBLY_LOCATION_MESSAGES, REGION_TEXT_LIMIT } from '@/constants/assembly'
import type { AssemblyAreaSearch, AssemblyLocationStatus, AssemblyRegionDraft } from '@/types/assembly'
import { prepareAssemblyRegion } from '@/utils/assemblyAreas'

const controlClass = 'min-h-12 w-full min-w-0 rounded-xl border border-border-subtle bg-card px-3 py-2 text-sm aria-invalid:border-red-700'

export function AssemblyAreaSearchPanel({ locationStatus, onLocate, onSearch, onEdit }: {
  locationStatus: AssemblyLocationStatus
  onLocate: () => void
  onSearch: (search: Extract<AssemblyAreaSearch, { mode: 'REGION' }>) => void
  onEdit: () => void
}) {
  const [draft, setDraft] = useState<AssemblyRegionDraft>({ province: '', district: '', neighborhood: '' })
  const [submitted, setSubmitted] = useState(false)
  const result = prepareAssemblyRegion(draft)
  const errors = submitted && !result.ok ? result.errors : {}

  function change(field: keyof AssemblyRegionDraft, value: string) {
    setDraft(field === 'province' ? { province: value, district: '', neighborhood: '' } : { ...draft, [field]: value })
    onEdit()
  }

  return (
    <section aria-labelledby="assembly-search-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-6">
      <h2 id="assembly-search-heading" className="text-xl font-semibold">Konum Seçimi</h2>
      <button type="button" disabled={locationStatus === 'loading'} onClick={() => { setSubmitted(false); onLocate() }}
        aria-describedby="assembly-location-privacy assembly-location-status"
        className="mt-5 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-brand-red bg-brand-red-soft px-3 py-3 text-sm font-semibold hover:bg-red-100 disabled:cursor-wait disabled:opacity-60">
        <LocateFixed size={20} aria-hidden="true" className="shrink-0 text-brand-red" />
        {locationStatus === 'loading' ? 'Konumunuz alınıyor…' : 'Konumumu Kullan'}
      </button>
      <p id="assembly-location-privacy" className="mt-3 text-xs leading-5 text-text-secondary">
        Konum paylaşımı isteğe bağlıdır. Konumunuz yalnızca bu sayfa açıkken kullanılır, kaydedilmez.
      </p>
      <p id="assembly-location-status" role="status" aria-live="polite" aria-atomic="true" className="mt-2 text-sm leading-6">
        {ASSEMBLY_LOCATION_MESSAGES[locationStatus]}
      </p>
      <div className="my-5 flex items-center gap-3 text-xs text-text-secondary" aria-hidden="true">
        <span className="h-px flex-1 bg-border-subtle" />veya<span className="h-px flex-1 bg-border-subtle" />
      </div>
      <form noValidate className="space-y-4" onSubmit={(event) => {
        event.preventDefault()
        setSubmitted(true)
        if (result.ok) onSearch(result.search)
        else event.currentTarget.querySelector<HTMLElement>(`[name="${Object.keys(result.errors)[0]}"]`)?.focus()
      }}>
        <div>
          <label htmlFor="assembly-province" className="mb-2 block text-sm font-medium">İl</label>
          <select id="assembly-province" name="province" required value={draft.province}
            onChange={(event) => change('province', event.target.value)} className={controlClass}
            aria-invalid={Boolean(errors.province)} aria-describedby={errors.province ? 'assembly-province-error' : undefined}>
            <option value="">İl seçin</option>
            {TURKEY_PROVINCES.map((province) => <option key={province}>{province}</option>)}
          </select>
          {errors.province ? <p id="assembly-province-error" role="alert" className="mt-2 text-sm text-red-700">{errors.province}</p> : null}
        </div>
        {([{ field: 'district', label: 'İlçe' }, { field: 'neighborhood', label: 'Mahalle' }] as const).map(({ field, label }) => (
          <div key={field}>
            <label htmlFor={`assembly-${field}`} className="mb-2 block text-sm font-medium">{label} <span className="font-normal text-text-secondary">(isteğe bağlı)</span></label>
            <input id={`assembly-${field}`} name={field} type="text" maxLength={REGION_TEXT_LIMIT} value={draft[field]}
              onChange={(event) => change(field, event.target.value)} className={controlClass}
              aria-invalid={Boolean(errors[field])} aria-describedby={errors[field] ? `assembly-${field}-error` : undefined} />
            {errors[field] ? <p id={`assembly-${field}-error`} role="alert" className="mt-2 text-sm text-red-700">{errors[field]}</p> : null}
          </div>
        ))}
        <button type="submit" className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-brand-red px-3 py-3 text-[19px] font-bold text-white hover:bg-red-600">
          <Search size={20} aria-hidden="true" className="shrink-0" />Alanları Göster
        </button>
      </form>
    </section>
  )
}
