import { useCallback, useState } from 'react'
import { History } from 'lucide-react'
import { EARTHQUAKE_LIMIT, FAULT_DISTANCE_KM, getFaultEarthquakes } from '@/api/earthquakes'
import { useApiResource } from '@/hooks/useApiResource'

export function FaultEarthquakeTable({ faultId }: { faultId: string }) {
  const [attempt, setAttempt] = useState(0)
  const load = useCallback((signal: AbortSignal) => getFaultEarthquakes(faultId, signal), [faultId])
  const result = useApiResource(`${faultId}:${attempt}`, load)
  return (
    <section aria-labelledby="fault-earthquakes-heading" className="min-w-0 p-4 sm:p-6" aria-busy={result.status === 'loading'}>
      <h3 id="fault-earthquakes-heading" className="flex items-center gap-3 font-semibold">
        <History size={20} className="shrink-0 text-brand-red-foreground" aria-hidden="true" />Yakındaki Depremler
      </h3>
      <p className="mt-3 text-xs leading-5 text-text-secondary">Fay çizgisine en fazla {FAULT_DISTANCE_KM} km uzaklıktaki, büyüklüğü en az 5 olan kayıtlar; en yeni kayıt önce gösterilir. Yakınlık, depremin bu fay üzerinde gerçekleştiğini kanıtlamaz. AFAD kayıtları anlık olmayabilir.</p>
      {result.status === 'loading' ? <p role="status" className="mt-4 text-sm">Deprem kayıtları alınıyor…</p> : null}
      {result.status === 'error' ? <div role="alert" className="mt-4 text-sm"><p>Deprem verileri alınırken bir sorun oluştu.</p>
        <button type="button" onClick={() => setAttempt(value => value + 1)} className="mt-2 min-h-11 rounded-lg border border-border-subtle px-4">Depremleri Yeniden Getir</button></div> : null}
      {result.status === 'success' ? <>
        {!result.data.earthquakes.length ? <p role="status" className="mt-4 text-sm leading-6">Bu uzaklık ve büyüklük koşullarına uyan deprem kaydı bulunmuyor.</p> : <div className="mt-4 overflow-x-auto" tabIndex={0} role="region" aria-label="Yakındaki deprem kayıtları tablosu">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Seçili fay çizgisine coğrafi olarak yakın deprem kayıtları</caption>
            <thead className="border-b border-border-subtle text-text-secondary"><tr>
              {['Tarih (UTC)', 'Konum', 'Büyüklük', 'Derinlik', 'Uzaklık'].map(label => <th key={label} scope="col" className="py-3 pr-3 font-medium">{label}</th>)}
            </tr></thead>
            <tbody>{result.data.earthquakes.map(event => <tr key={event.id} className="border-b border-border-subtle last:border-0">
              <td className="py-3 pr-3"><time dateTime={event.date}>{new Date(event.date).toLocaleString('tr-TR', { timeZone: 'UTC' })}</time></td>
              <td className="py-3 pr-3">{event.location ?? 'Konum adı belirtilmemiş'}</td>
              <td className="py-3 pr-3 font-semibold text-brand-red-foreground">{event.magnitude} {event.magnitudeType}</td>
              <td className="py-3 pr-3">{event.depthKm} km</td>
              <td className="py-3">{event.distanceKm} km</td>
            </tr>)}</tbody>
          </table>
        </div>}
        {result.data.earthquakes.length === EARTHQUAKE_LIMIT ? <p className="mt-3 text-xs">İlk {EARTHQUAKE_LIMIT} kayıt gösteriliyor; daha eski kayıtlar olabilir.</p> : null}
        <p className="mt-3 text-xs leading-5 text-text-secondary">{result.data.attribution} · {result.data.faultAttribution} · {result.data.faultLicense}</p>
      </> : null}
    </section>
  )
}
