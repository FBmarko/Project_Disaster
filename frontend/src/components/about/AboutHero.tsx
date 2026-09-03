import { Activity } from 'lucide-react'
import { BrandLogo } from '@/components/common/BrandLogo'

export function AboutHero() {
  return (
    <header className="relative overflow-hidden rounded-2xl border border-border-subtle/70 bg-card px-5 py-8 shadow-sm sm:px-8 sm:py-10 lg:px-12">
      <div
        className="absolute top-0 left-0 h-full w-1 bg-brand-red"
        aria-hidden="true"
      />
      <div className="relative max-w-3xl">
        <div className="mb-6 flex items-center gap-4">
          <BrandLogo height={44} />
          <span className="hidden h-8 w-px bg-border-subtle sm:block" aria-hidden="true" />
          <span className="hidden items-center gap-2 text-sm font-medium text-text-secondary sm:flex">
            <Activity size={17} className="text-brand-red" aria-hidden="true" />
            Afet farkındalığı ve analiz arayüzü
          </span>
        </div>
        <h1 className="sr-only">AFET360 Hakkında</h1>
        <p className="text-xl leading-8 font-semibold tracking-tight text-text-primary sm:text-2xl sm:leading-9">
          Deprem verilerini, fay hatlarını ve simülasyon senaryolarını anlaşılır
          bir arayüzde bir araya getirmeyi amaçlayan bir afet farkındalığı ve
          analiz platformu.
        </p>
      </div>
    </header>
  )
}
