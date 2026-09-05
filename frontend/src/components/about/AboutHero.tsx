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
          Depremle ilgili bilgileri incelemek, senaryo ayarlarını keşfetmek ve
          daha hazırlıklı olmak için bir afet farkındalık platformu.
        </p>
        
      </div>
    </header>
  )
}
