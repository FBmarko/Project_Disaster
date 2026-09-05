import { Backpack, ClipboardList, ListChecks, MessagesSquare, UsersRound } from 'lucide-react'
import type { PreparednessGuide } from '@/types/preparedness'
import { GuideSection } from './GuideSection'
import { PreparednessSafetyNotice } from './PreparednessSafetyNotice'

/** Accept structured, validated data from the project backend when its contract is available. */
export function PreparednessGuideResults({ guide }: { guide: PreparednessGuide | null }) {
  return (
    <section aria-labelledby="preparedness-results-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-7">
      <h2 id="preparedness-results-heading" className="text-xl font-semibold">Hazırlık Rehberiniz</h2>
      {!guide ? (
        <div className="my-6 rounded-xl border border-dashed border-border-subtle bg-surface px-4 py-7 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-card text-brand-red-foreground shadow-sm">
            <ClipboardList size={25} aria-hidden="true" />
          </span>
          <p className="mt-4 font-medium">Hazırlık, evinizi tanımakla başlar</p>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-text-secondary">Bilgilerinizi tamamlayın. Kişisel rehberiniz için gerekli ilk adımı atın.</p>
        </div>
      ) : null}
      <div className="mt-5 grid gap-3">
        <GuideSection id="guide-priorities" title="Öncelikler" icon={ListChecks} items={guide?.priorities ?? null} />
        <GuideSection id="guide-kit" title="Afet Çantası" icon={Backpack} items={guide?.emergencyKit ?? null} />
        <GuideSection id="guide-communication" title="İletişim Planı" icon={MessagesSquare} items={guide?.communicationPlan ?? null} />
        <GuideSection id="guide-special-needs" title="Özel İhtiyaçlar" icon={UsersRound} items={guide?.specialNeeds ?? null} />
      </div>
      <div className="mt-5"><PreparednessSafetyNotice /></div>
    </section>
  )
}
