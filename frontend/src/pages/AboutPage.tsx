import {
  Activity,
  BookOpen,
  ClipboardCheck,
  Compass,
  Layers3,
  Lightbulb,
  MapPinned,
  ShieldCheck,
  SlidersHorizontal,
  UsersRound,
  Waypoints,
} from 'lucide-react'
import { AboutHero } from '@/components/about/AboutHero'
import { AboutSection } from '@/components/about/AboutSection'
import { ModuleCard } from '@/components/about/ModuleCard'
import { SafetyNotice } from '@/components/about/SafetyNotice'

export function AboutPage() {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 sm:space-y-6">
      <AboutHero />

      <AboutSection id="afet360-nedir" title="AFET360 Nedir?" icon={Compass}>
        <p>
          AFET360, deprem konusunda farkındalığı artırmak, yaşadığınız bölgeyi
          daha iyi tanımanızı sağlamak ve olası bir deprem öncesinde hazırlıklı
          olmanıza yardımcı olmak için tasarlanmış bir afet bilgilendirme ve
          hazırlık platformudur.
        </p>
        <p>
          Harita tabanlı araçları, deprem senaryolarını ve kişisel hazırlık
          rehberlerini bir araya getirerek bilgiyi günlük yaşamınızda
          atabileceğiniz somut adımlarla buluşturur.
        </p>
      </AboutSection>

      <AboutSection id="neler-yapabilirsiniz" title="Neler Yapabilirsiniz?" icon={Layers3}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
          <ModuleCard
            icon={MapPinned}
            title="Deprem Haritası"
            description="Türkiye haritası üzerinden şehirleri inceleyin ve depremle ilgili bölgesel bilgileri daha anlaşılır bir şekilde keşfedin."
            className="lg:col-span-2"
          />
          <ModuleCard
            icon={Waypoints}
            title="Fay Hatlarını İnceleyin"
            description="Türkiye üzerindeki aktif fay hatlarını haritada görüntüleyin ve farklı bölgelerdeki fay yapılarını inceleyin."
            className="lg:col-span-2"
          />
          <ModuleCard
            icon={SlidersHorizontal}
            title="Deprem Senaryosu Oluşturun"
            description="Haritadan bir konum seçin; deprem büyüklüğü, derinlik ve etki alanını belirleyerek farklı senaryoları deneyimleyin."
            className="lg:col-span-2"
          />
          <ModuleCard
            icon={ClipboardCheck}
            title="Hazırlık Rehberi"
            description="Kendiniz, aileniz ve yaşam koşullarınız için kişiselleştirilmiş afet hazırlık önerileri oluşturun."
            className="lg:col-span-3"
          />
          <ModuleCard
            icon={UsersRound}
            title="Toplanma Alanları"
            description="Bölgenizdeki toplanma alanlarını harita üzerinden inceleyin ve ihtiyaç anında ulaşabileceğiniz noktaları önceden tanıyın."
            className="sm:col-span-2 lg:col-span-3"
          />
        </div>
      </AboutSection>

      <AboutSection id="deprem-simulasyonu" title="Deprem Simülasyonu" icon={Activity}>
        <p>
          Deprem simülasyonu, farklı büyüklük ve derinliklerdeki deprem
          senaryolarının olası etkilerini daha anlaşılır şekilde
          deneyimlemenize yardımcı olur.
        </p>
        <p>
          Amaç bir depremin ne zaman gerçekleşeceğini tahmin etmek değil;
          olası bir senaryo üzerinden çevrenizi, riskleri ve hazırlık
          ihtiyaçlarınızı daha iyi anlamaktır.
        </p>
        <p>
          Senaryoyu inceleyerek kendiniz, aileniz ve yaşam alanınız için hangi
          önlemleri alabileceğinizi değerlendirebilirsiniz.
        </p>
      </AboutSection>

      <AboutSection id="neden-afet360" title="Neden AFET360?" icon={Lightbulb}>
        <div className="grid gap-4 md:grid-cols-3">
          <ModuleCard
            icon={BookOpen}
            title="Bilgi"
            description="Depremle ilgili coğrafi bilgileri sade ve anlaşılır bir arayüz üzerinden inceleyin."
          />
          <ModuleCard
            icon={Lightbulb}
            title="Farkındalık"
            description="Farklı deprem senaryolarını değerlendirerek yaşadığınız çevreye yönelik farkındalığınızı artırın."
          />
          <ModuleCard
            icon={ShieldCheck}
            title="Hazırlık"
            description="Afet öncesinde atabileceğiniz adımları öğrenin ve kendiniz için uygulanabilir bir hazırlık planı oluşturun."
          />
        </div>
      </AboutSection>

      <SafetyNotice />
    </div>
  )
}
