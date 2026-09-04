import { useState } from 'react'
import { LocateFixed, Search } from 'lucide-react'
import { ASSEMBLY_LOCATION_MESSAGES } from '@/constants/assembly'
import type { AssemblyCoordinates, AssemblyLocationStatus } from '@/types/assembly'

export function AssemblyAreaSearchPanel({ locationStatus, loading, onLocate, onSearch, onEdit }: {
  locationStatus: AssemblyLocationStatus
  loading: boolean
  onLocate: (radiusKm: number) => void
  onSearch: (point: AssemblyCoordinates, radiusKm: number) => void
  onEdit: () => void
}) {
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius] = useState('5')
  const [error, setError] = useState('')
  const validRadius = radius.trim() !== '' && Number.isFinite(Number(radius)) && Number(radius) > 0 && Number(radius) <= 200
  const controlClass = 'min-h-12 w-full min-w-0 rounded-xl border border-border-subtle bg-card px-3 py-2 text-sm'
  return (
    <section aria-labelledby="assembly-search-heading" className="min-w-0 rounded-2xl border border-border-subtle bg-card p-5 shadow-sm sm:p-6">
      <h2 id="assembly-search-heading" className="text-xl font-semibold">Konum Seçimi</h2>
      <p className="mt-3 text-sm leading-6 text-text-secondary">Konumunuzu paylaşın veya enlem ve boylam girin. İl, ilçe ve mahalle adıyla arama şu anda sunulmuyor.</p>
      <label htmlFor="assembly-radius" className="mt-4 mb-2 block text-sm font-medium">Arama yarıçapı (km)</label>
      <input id="assembly-radius" type="number" min="0.01" max="200" step="any" value={radius}
        onChange={event => { setRadius(event.target.value); setError(''); onEdit() }} className={controlClass} aria-describedby="assembly-radius-hint" />
      <p id="assembly-radius-hint" className="mt-2 text-xs leading-5 text-text-secondary">0'dan büyük, en fazla 200 km. Arama uzaklığı güvenli tahliye veya yürüyüş mesafesi değildir.</p>
      <button type="button" disabled={loading || locationStatus === 'loading' || !validRadius} onClick={() => { setError(''); onLocate(Number(radius)) }}
        aria-describedby="assembly-location-privacy assembly-location-status"
        className="mt-5 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-brand-red bg-brand-red-soft px-3 py-3 text-sm font-semibold hover:bg-red-100 disabled:opacity-60">
        <LocateFixed size={20} aria-hidden="true" className="shrink-0 text-brand-red" />
        {locationStatus === 'loading' ? 'Konumunuz alınıyor…' : 'Konumumu Kullan'}
      </button>
      <p id="assembly-location-privacy" className="mt-3 text-xs leading-5 text-text-secondary">Konum paylaşımı isteğe bağlıdır. Bu düğmeyle konumunuz yakındaki noktaları aramak için gönderilir. Tarayıcıda kalıcı olarak saklanmaz.</p>
      <p id="assembly-location-status" role="status" aria-live="polite" className="mt-2 text-sm leading-6">{ASSEMBLY_LOCATION_MESSAGES[locationStatus]}</p>
      <form noValidate className="mt-5 space-y-4 border-t border-border-subtle pt-5" onSubmit={event => {
        event.preventDefault()
        if (!validRadius) { setError('Lütfen 0 ile 200 km arasında geçerli bir arama yarıçapı girin.'); document.getElementById('assembly-radius')?.focus(); return }
        const lat = Number(latitude), lon = Number(longitude)
        if (!latitude.trim() || !Number.isFinite(lat) || Math.abs(lat) > 90) { setError('Lütfen -90 ile 90 arasında geçerli bir enlem girin.'); event.currentTarget.querySelector<HTMLInputElement>('[name="latitude"]')?.focus(); return }
        if (!longitude.trim() || !Number.isFinite(lon) || Math.abs(lon) > 180) { setError('Lütfen -180 ile 180 arasında geçerli bir boylam girin.'); event.currentTarget.querySelector<HTMLInputElement>('[name="longitude"]')?.focus(); return }
        if (loading) return
        setError(''); onSearch({ latitude: lat, longitude: lon }, Number(radius))
      }}>
        <div><label htmlFor="assembly-latitude" className="mb-2 block text-sm font-medium">Enlem</label>
          <input id="assembly-latitude" name="latitude" type="number" min="-90" max="90" step="any" value={latitude} className={controlClass}
            onChange={event => { setLatitude(event.target.value); setError(''); onEdit() }} /></div>
        <div><label htmlFor="assembly-longitude" className="mb-2 block text-sm font-medium">Boylam</label>
          <input id="assembly-longitude" name="longitude" type="number" min="-180" max="180" step="any" value={longitude} className={controlClass}
            onChange={event => { setLongitude(event.target.value); setError(''); onEdit() }} /></div>
        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
        <button type="submit" disabled={loading || locationStatus === 'loading'} className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-brand-red px-3 py-3 text-[19px] font-bold text-white hover:bg-red-600 disabled:opacity-60">
          <Search size={20} aria-hidden="true" className="shrink-0" />{loading ? 'Alanlar Aranıyor…' : 'Alanları Göster'}
        </button>
      </form>
    </section>
  )
}
