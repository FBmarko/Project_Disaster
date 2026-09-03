import { MapPin } from 'lucide-react'

export function FaultCities({ cities, pending }: { cities: readonly string[]; pending: boolean }) {
  return (
    <section aria-labelledby="fault-cities-heading" className="min-w-0 p-4 sm:p-6">
      <h3 id="fault-cities-heading" className="flex items-center gap-3 font-semibold">
        <MapPin size={20} className="shrink-0 text-brand-red" aria-hidden="true" /> Üzerinden Geçtiği Şehirler
      </h3>
      {cities.length ? <ul className="mt-5 flex flex-wrap gap-2">
        {cities.map((city) => <li key={city} className="max-w-full break-words rounded-full border border-border-subtle px-4 py-2 text-sm">{city}</li>)}
      </ul> : <p className="mt-5 text-sm leading-6 text-text-secondary">{pending
        ? 'Bu fay hattı için şehir verisi backend entegrasyonu sonrasında gösterilecektir.'
        : 'Bu fay hattı için şehir kaydı bulunmuyor.'}</p>}
    </section>
  )
}
