import { History } from 'lucide-react'
import type { FaultEarthquake } from '@/types/fault'

export function FaultEarthquakeTable({ earthquakes, pending }: { earthquakes: readonly FaultEarthquake[]; pending: boolean }) {
  return (
    <section aria-labelledby="fault-earthquakes-heading" className="min-w-0 p-4 sm:p-6">
      <h3 id="fault-earthquakes-heading" className="flex items-center gap-3 font-semibold">
        <History size={20} className="shrink-0 text-brand-red" aria-hidden="true" /> Geçmiş Depremler
      </h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Seçili fay segmentine ait geçmiş deprem kayıtları</caption>
          <thead className="border-b border-border-subtle text-text-secondary"><tr>
            <th scope="col" className="py-3 pr-3 font-medium">Tarih</th>
            <th scope="col" className="py-3 pr-3 font-medium">Konum</th>
            <th scope="col" className="py-3 text-right font-medium">Büyüklük</th>
          </tr></thead>
          <tbody>{earthquakes.length ? earthquakes.map((earthquake) => <tr key={earthquake.id} className="border-b border-border-subtle last:border-0">
            <td className="py-3 pr-3">{earthquake.date}</td>
            <td className="py-3 pr-3">{earthquake.location}</td>
            <td className="py-3 text-right font-semibold text-brand-red">{earthquake.magnitude}</td>
          </tr>) : <tr><td colSpan={3} className="py-5 leading-6 text-text-secondary">{pending
            ? 'Geçmiş deprem verileri backend entegrasyonu tamamlandığında gösterilecektir.'
            : 'Bu fay hattı için geçmiş deprem kaydı bulunmuyor.'}</td></tr>}</tbody>
        </table>
      </div>
    </section>
  )
}
