import { ShieldAlert } from 'lucide-react'

export function SafetyNotice() {
  return (
    <aside
      aria-labelledby="safety-notice-heading"
      className="rounded-2xl border border-brand-red/25 bg-brand-red-soft p-5 sm:p-7"
    >
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:gap-4">
        <span
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-card text-brand-red shadow-sm"
          aria-hidden="true"
        >
          <ShieldAlert size={23} />
        </span>
        <div>
          <h2 id="safety-notice-heading" className="text-lg font-semibold text-text-primary">
            Önemli Bilgilendirme
          </h2>
          <p className="mt-2 text-sm leading-6 text-text-primary sm:text-[15px] sm:leading-7">
            AFET360 bilgilendirme, farkındalık ve hazırlık amacı taşır.
            Depremleri önceden tahmin eden, erken uyarı veren veya resmî acil
            durum yönlendirmesi sağlayan bir sistem değildir. Afet ve acil
            durumlarda AFAD ve ilgili resmî kurumların açıklama ve talimatlarını
            takip edin.
          </p>
        </div>
      </div>
    </aside>
  )
}
