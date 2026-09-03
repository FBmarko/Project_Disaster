import {
  Activity,
  ChartNoAxesCombined,
  Database,
  Goal,
  House,
  Layers3,
  MapPinned,
  SlidersHorizontal,
  Waypoints,
} from 'lucide-react'
import { AboutHero } from '@/components/about/AboutHero'
import { AboutSection } from '@/components/about/AboutSection'
import { DataSourceCard } from '@/components/about/DataSourceCard'
import { ModuleCard } from '@/components/about/ModuleCard'
import { SafetyNotice } from '@/components/about/SafetyNotice'

export function AboutPage() {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 sm:space-y-6">
      <AboutHero />

      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        <AboutSection id="afet360-nedir" title="AFET360 Nedir?" icon={Activity}>
          <p>
            AFET360, Türkiye&apos;deki deprem tehlikesi ve aktif fay verilerini
            harita tabanlı bir arayüz üzerinden incelemeyi ve kullanıcıların
            belirledikleri konumlar için deprem senaryoları hazırlayabilmesini
            amaçlayan web tabanlı bir bilgi ve senaryo arayüzüdür.
          </p>
          <p>
            Uygulama bir deprem tahmin sistemi değildir; depremlerin ne zaman
            gerçekleşeceğini öngörmez.
          </p>
        </AboutSection>

        <AboutSection id="projenin-amaci" title="Projenin Amacı" icon={Goal}>
          <ul className="space-y-3" role="list">
            {[
              'Depremle ilgili coğrafi bilgilerin incelenmesini kolaylaştırmak',
              'İl sınırlarını ve aktif fay geometrilerini anlaşılır biçimde görselleştirmek',
              'Kullanıcı tanımlı deprem senaryosu girdilerini hazırlamak',
              'Gelecekteki backend tabanlı analiz sonuçları için sağlam bir arayüz oluşturmak',
            ].map((goal) => (
              <li key={goal} className="flex items-start gap-3">
                <span
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-red"
                  aria-hidden="true"
                />
                <span>{goal}</span>
              </li>
            ))}
          </ul>
        </AboutSection>
      </div>

      <AboutSection id="uygulama-modulleri" title="Uygulama Modülleri" icon={Layers3}>
        <div className="grid gap-3 sm:grid-cols-2">
          <ModuleCard
            icon={House}
            title="Ana Sayfa"
            description="Türkiye il haritası ve geliştirme amaçlı geçici risk görünümü."
          />
          <ModuleCard
            icon={Waypoints}
            title="Fay Hatları"
            description="Türkiye görünümündeki kaynak tabanlı aktif fay geometrilerinin incelenmesi."
          />
          <ModuleCard
            icon={SlidersHorizontal}
            title="Deprem Simülasyonu"
            description="Harita üzerinden konum, büyüklük, derinlik ve etki yarıçapı seçimi."
          />
          <ModuleCard
            icon={ChartNoAxesCombined}
            title="Simülasyon Sonuçları"
            description="Backend simülasyon sistemi tamamlandığında senaryo sonuçlarının sunulması planlanan bölüm."
            status="Planlandı"
          />
        </div>
      </AboutSection>

      <AboutSection id="veri-kaynaklari" title="Veri Kaynakları" icon={Database}>
        <p className="mb-5 max-w-3xl">
          İl sınırı ve aktif fay katmanları uygulama paketinde yerel olarak
          saklanır. Bu katmanlar için çalışma sırasında AFAD veya GEM&apos;den
          veri indirilmez.
        </p>
        <div className="grid gap-4 lg:grid-cols-2">
          <DataSourceCard
            title="Türkiye İl Sınırları"
            source="alpers/Turkey-Maps-GeoJSON"
            sourceHref="https://github.com/alpers/Turkey-Maps-GeoJSON"
            license="Apache Lisansı 2.0"
            licenseHref="https://github.com/alpers/Turkey-Maps-GeoJSON/blob/master/LICENSE"
            description="81 ilin sınır geometrileri kaynak dosyadaki koordinatlar değiştirilmeden yerel GeoJSON olarak kullanılır."
          />
          <DataSourceCard
            title="Aktif Fay Geometrileri"
            source="GEM Global Active Faults Database"
            sourceHref="https://github.com/GEMScienceTools/gem-global-active-faults"
            license="CC BY-SA 4.0"
            licenseHref="https://creativecommons.org/licenses/by-sa/4.0/"
            description="EMME kataloğundan Türkiye görünümü için filtrelenen bir alt kümedir; kaynak koordinatları korunmuştur. Resmî veya eksiksiz bir ulusal envanter değildir. GEM desteği veya onayı ima edilmez."
            attribution="GEM Foundation · Styron ve Pagani (2020). Türetilmiş fay verisi ve görsel katmanı CC BY-SA 4.0 kapsamında paylaşılır."
          />
        </div>
      </AboutSection>

      <AboutSection id="veri-hakkinda" title="Veri Hakkında" icon={MapPinned}>
        <div className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-border-subtle bg-surface/70 p-4 sm:p-5">
            <h3 className="font-semibold text-text-primary">
              Kaynağa Dayalı Coğrafi Veriler
            </h3>
            <p className="mt-2">
              İl sınırları ile aktif fay geometrileri açık coğrafi kaynaklara
              dayanır. Aktif fay katmanı kaynak geometrisini ve katalog
              bilgisini görselleştirir; tek başına bir tehlike veya risk
              değerlendirmesi oluşturmaz.
            </p>
          </article>
          <article className="rounded-xl border border-brand-red/20 bg-brand-red-soft p-4 sm:p-5">
            <h3 className="font-semibold text-text-primary">
              Geliştirme ve Backend Bekleyen Veriler
            </h3>
            <p className="mt-2 text-text-primary">
              İl haritasındaki DÜŞÜK / ORTA / YÜKSEK değerleri, arayüz
              davranışını göstermek için kullanılan geçici örnek verilerdir.
              Fayların şehir ve deprem ilişkileri ile simülasyon sonuçları da
              backend geliştirmesine bağlıdır. Bu içerikler bilimsel veya
              resmî risk değerlendirmesi olarak yorumlanmamalıdır.
            </p>
          </article>
        </div>
      </AboutSection>

      <AboutSection id="simulasyon-hakkinda" title="Simülasyon Hakkında" icon={SlidersHorizontal}>
        <p>
          Deprem Simülasyonu sayfası şu anda yalnızca konum, deprem büyüklüğü,
          derinlik ve etki yarıçapı gibi senaryo girdilerini hazırlar. Bilimsel
          simülasyon hesaplaması ve sonuç üretimi, gelecekteki backend
          entegrasyonuna bağlıdır.
        </p>
        <p>
          Mevcut frontend; can kaybı, bina hasarı, nüfus veya altyapı etkisi,
          olasılık ya da gerçek deprem sonucu hesaplamaz.
        </p>
      </AboutSection>

      <SafetyNotice />
    </div>
  )
}
