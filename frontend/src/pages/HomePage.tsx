import { RiskLegend } from '@/components/map/RiskLegend'
import { TurkeyRiskMap } from '@/components/map/TurkeyRiskMap'
import { useProvinceHazard } from '@/hooks/useProvinceHazard'

/**
 * Landing page: the province earthquake hazard map with its continuous numeric legend.
 *
 * Visualizes spatial median Peak Ground Acceleration (PGA in g) across Turkey's
 * 81 provinces derived from the GEM Global Seismic Hazard Map (GSHM v2026.1).
 */
export function HomePage() {
  const { data, isLoading, error } = useProvinceHazard()

  return (
    <section className="w-full rounded-2xl border border-border-subtle/70 bg-card p-3 shadow-sm sm:p-6 lg:p-8">
      <h1 className="sr-only">Türkiye il bazlı deprem tehlike haritası</h1>

      {error ? (
        <div
          role="alert"
          className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-700"
        >
          {error} Harita nötr durumda gösterilmektedir.
        </div>
      ) : null}

      <TurkeyRiskMap hazards={data} isLoading={isLoading} />

      <div className="mt-4 sm:mt-6">
        <RiskLegend
          minPga={data?.minMedianPga}
          maxPga={data?.maxMedianPga}
        />
      </div>

      <div className="mt-4 border-t border-border-subtle/60 pt-3 text-xs leading-relaxed text-text-secondary">
        <p>
          Bu gösterim GEM GSHM v2026.1 referans-kaya PGA (en büyük yer ivmesi, 475 yıllık dönüş
          periyodu, Vs30 = 800 m/s) verisinin il bazındaki mekânsal medyan özetidir. Yerel zemin ve
          bina özelliklerini içermez ve risk değerlendirmesi değildir. Resmî değerlendirme ve
          tasarım kararlarında AFAD ve yürürlükteki TBDY kaynakları esas alınmalıdır.
        </p>
        <p className="mt-1 text-[11px] text-text-muted">
          Tehlike verisi: Global Earthquake Model Foundation (GSHM v2026.1, CC BY-NC-SA 4.0). İl
          sınırları: alpers/Turkey-Maps-GeoJSON (Apache-2.0).
        </p>
      </div>
    </section>
  )
}
