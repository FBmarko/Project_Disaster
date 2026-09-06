import { AlertCircle, ClipboardCheck } from 'lucide-react'
import { useEffect, useReducer, useRef, useState } from 'react'
import { getPreparednessErrorMessage, getPreparednessGuide } from '@/api/preparedness'
import { PreparednessForm } from '@/components/preparedness/PreparednessForm'
import { PreparednessGuideResults } from '@/components/preparedness/PreparednessGuideResults'
import type { PreparednessAction, PreparednessGuide } from '@/types/preparedness'
import { createPreparednessState, preparednessReducer, preparePreparednessProfile } from '@/utils/preparednessDraft'

export function PreparednessGuidePage() {
  const [state, dispatch] = useReducer(preparednessReducer, undefined, createPreparednessState)
  const [guide, setGuide] = useState<PreparednessGuide | null>(null)
  const [disclaimer, setDisclaimer] = useState<string | undefined>(undefined)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const handleAction = async (action: PreparednessAction) => {
    dispatch(action)

    if (action.type === 'change') {
      if (error) {
        setError(null)
      }
      return
    }

    if (action.type === 'submit') {
      const result = preparePreparednessProfile(state.draft)
      if (!result.ok) {
        return
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      const controller = new AbortController()
      abortControllerRef.current = controller

      setIsLoading(true)
      setError(null)

      try {
        const response = await getPreparednessGuide(result.profile, controller.signal)
        setGuide(response.guide)
        setDisclaimer(response.disclaimer)
        setError(null)
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          return
        }
        setGuide(null)
        setError(getPreparednessErrorMessage(err))
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 sm:space-y-6">
      <header className="rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-8">
        <div className="mb-4 flex items-center gap-2 text-sm font-medium text-text-secondary">
          <ClipboardCheck size={19} aria-hidden="true" className="text-brand-red-foreground" />Hazırlık Rehberi
        </div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Kişisel Hazırlık Rehberi</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary sm:text-base">
          Yaşam koşullarınız hakkında birkaç bilgi verin. Afet öncesi hazırlığınız için
          şehrinizi ve evinizdeki kişilerin ihtiyaçlarını bir araya getirin.
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="flex items-center gap-3 rounded-xl border border-error/20 bg-error/10 p-4 text-sm font-medium text-error"
        >
          <AlertCircle size={20} className="shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid items-start gap-5 sm:gap-6 lg:grid-cols-2">
        <PreparednessForm state={state} onAction={handleAction} isLoading={isLoading} />
        <PreparednessGuideResults guide={guide} disclaimer={disclaimer} isLoading={isLoading} />
      </div>
    </div>
  )
}
