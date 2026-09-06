import { Backpack, ClipboardList, Info, ListChecks, Loader2, MessagesSquare, UsersRound } from 'lucide-react'
import type { PreparednessGuide } from '@/types/preparedness'
import { GuideSection } from './GuideSection'
import { PreparednessSafetyNotice } from './PreparednessSafetyNotice'

interface PreparednessGuideResultsProps {
  guide: PreparednessGuide | null
  disclaimer?: string
  isLoading?: boolean
}

export function PreparednessGuideResults({ guide, disclaimer, isLoading }: PreparednessGuideResultsProps) {
  return (
    <section aria-labelledby="preparedness-results-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-7">
      <h2 id="preparedness-results-heading" className="text-xl font-semibold">Hazırlık Rehberiniz</h2>

      {isLoading ? (
        <div className="my-6 flex flex-col items-center justify-center rounded-xl border border-border-subtle bg-surface px-4 py-10 text-center" role="status">
          <Loader2 size={32} className="animate-spin text-brand-red-foreground" aria-hidden="true" />
          <p className="mt-4 font-medium">Hazırlık rehberi oluşturuluyor...</p>
          <p className="mt-1 text-sm text-text-secondary">Hane bilgilerinize uygun öneriler derleniyor.</p>
        </div>
      ) : !guide ? (
        <div className="my-6 rounded-xl border border-dashed border-border-subtle bg-surface px-4 py-7 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-card text-brand-red-foreground shadow-sm">
            <ClipboardList size={25} aria-hidden="true" />
          </span>
          <p className="mt-4 font-medium">Hazırlık, evinizi tanımakla başlar</p>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-text-secondary">Bilgilerinizi tamamlayın. Kişisel rehberiniz için gerekli ilk adımı atın.</p>
        </div>
      ) : (
        <>
          {guide.summary ? (
            <div className="mt-4 rounded-xl border border-border-subtle bg-surface p-4 text-sm leading-6 text-text-primary">
              <p className="font-medium text-text-primary">{guide.summary}</p>
            </div>
          ) : null}
          <div className="mt-5 grid gap-3">
            <GuideSection id="guide-priorities" title="Öncelikler" icon={ListChecks} items={guide.priorities} />
            <GuideSection id="guide-kit" title="Acil Durum Çantası" icon={Backpack} items={guide.emergencyKit} />
            <GuideSection id="guide-communication" title="İletişim Planı" icon={MessagesSquare} items={guide.communicationPlan} />
            <GuideSection id="guide-special-needs" title="Özel İhtiyaçlar" icon={UsersRound} items={guide.specialNeeds} />
            <GuideSection id="guide-important-notes" title="Önemli Notlar" icon={Info} items={guide.importantNotes} />
          </div>
        </>
      )}

      <div className="mt-5">
        <PreparednessSafetyNotice disclaimer={disclaimer} />
      </div>
    </section>
  )
}
