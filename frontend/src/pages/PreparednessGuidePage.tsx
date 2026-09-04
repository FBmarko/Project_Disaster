import { ClipboardCheck } from 'lucide-react'
import { useReducer } from 'react'
import { PreparednessForm } from '@/components/preparedness/PreparednessForm'
import { PreparednessGuideResults } from '@/components/preparedness/PreparednessGuideResults'
import { createPreparednessState, preparednessReducer } from '@/utils/preparednessDraft'

export function PreparednessGuidePage() {
  const [state, dispatch] = useReducer(preparednessReducer, undefined, createPreparednessState)

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 sm:space-y-6">
      <header className="rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-8">
        <div className="mb-4 flex items-center gap-2 text-sm font-medium text-text-secondary">
          <ClipboardCheck size={19} aria-hidden="true" className="text-brand-red" />Hazırlık Rehberi
        </div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Kişisel Hazırlık Rehberi</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary sm:text-base">
          Yaşam koşullarınız hakkında birkaç bilgi verin. Afet öncesi hazırlığınız için
          şehrinizi ve evinizdeki kişilerin ihtiyaçlarını bir araya getirin.
        </p>
      </header>
      <div className="grid items-start gap-5 sm:gap-6 lg:grid-cols-2">
        <PreparednessForm state={state} onAction={dispatch} />
        {/* No guide exists until a future project-backend integration supplies structured data. */}
        <PreparednessGuideResults guide={null} />
      </div>
    </div>
  )
}
