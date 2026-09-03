import { ArrowRight } from 'lucide-react'
import { BrandLogo } from '@/components/common/BrandLogo'

export function AboutHero() {
  return (
    <header className="relative overflow-hidden rounded-2xl border border-border-subtle/70 bg-card px-5 py-8 shadow-sm sm:px-8 sm:py-10 lg:px-12">
      <div
        className="absolute top-0 left-0 h-full w-1 bg-brand-red"
        aria-hidden="true"
      />
      <div className="relative max-w-3xl">
        <h1 className="mb-6">
          <BrandLogo height={44} />
        </h1>
        <p className="text-xl leading-8 font-semibold tracking-tight text-text-primary sm:text-2xl sm:leading-9">
          Depremi anlamak, olası senaryoları deneyimlemek ve daha hazırlıklı
          olmak için bir afet farkındalık platformu.
        </p>
        <ol aria-label="AFET360 yaklaşımı" className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm font-medium text-text-primary">
          <li>
            <span className="flex items-center gap-3">
              Bilgi <ArrowRight size={15} className="text-brand-red" aria-hidden="true" />
            </span>
          </li>
          <li>
            <span className="flex items-center gap-3">
              Farkındalık <ArrowRight size={15} className="text-brand-red" aria-hidden="true" />
            </span>
          </li>
          <li>Hazırlık</li>
        </ol>
      </div>
    </header>
  )
}
