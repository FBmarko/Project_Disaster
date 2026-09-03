import { RiskLegend } from '@/components/map/RiskLegend'
import { TurkeyRiskMap } from '@/components/map/TurkeyRiskMap'
import { useProvinceRisk } from '@/hooks/useProvinceRisk'

/**
 * Landing page: the province risk map with its legend, composed from the map
 * components. Layout follows `docs/ui-reference/home-page.png` — one wide white
 * card holding the map, with the legend beneath it.
 */
export function HomePage() {
  const riskByProvince = useProvinceRisk()

  return (
    <section className="w-full rounded-2xl border border-border-subtle/70 bg-card p-3 shadow-sm sm:p-6 lg:p-8">
      <h1 className="sr-only">Türkiye il bazlı deprem risk haritası</h1>

      <TurkeyRiskMap riskByProvince={riskByProvince} />

      <div className="mt-4 sm:mt-6">
        <RiskLegend />
      </div>

      <p className="mt-3 text-xs text-text-secondary">
        Haritadaki risk seviyeleri geliştirme amaçlı geçici örnek verilerdir;
        bilimsel bir deprem risk değerlendirmesi değildir.
      </p>
    </section>
  )
}
