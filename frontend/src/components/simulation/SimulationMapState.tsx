import { LoaderCircle, MapPin, TriangleAlert } from 'lucide-react'

export function SimulationMapState({ state }: { state: 'missing-key' | 'loading' | 'error' }) {
  const Icon = state === 'loading' ? LoaderCircle : state === 'error' ? TriangleAlert : MapPin
  return (
    <div className="flex h-full w-full items-center justify-center bg-surface p-6 text-center"
      role={state === 'error' ? 'alert' : 'status'} aria-live="polite">
      <div className="max-w-sm">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-border-subtle bg-card">
          <Icon size={26} aria-hidden="true" className={state === 'loading' ? 'text-brand-red-foreground motion-safe:animate-spin' : 'text-brand-red-foreground'} />
        </span>
        <p className="mt-4 font-semibold">{state === 'missing-key' ? 'Google Maps API anahtarı yapılandırılmamış.'
          : state === 'error' ? 'Google Maps yüklenemedi.' : 'Harita yükleniyor...'}</p>
        {state !== 'loading' ? <p className="mt-2 text-sm leading-6 text-text-secondary">{state === 'missing-key'
          ? 'Harita yapılandırıldığında buradan bir konum seçerek senaryonuzu hazırlayabilirsiniz.'
          : 'Bağlantınızı ve harita yapılandırmasını kontrol edip sayfayı yeniden yükleyin.'}</p> : null}
        {state === 'error' ? <button type="button" onClick={() => window.location.reload()}
          className="mt-4 min-h-11 rounded-lg border border-border-subtle bg-card px-4 text-sm font-medium hover:bg-brand-red-soft">Sayfayı Yenile</button> : null}
      </div>
    </div>
  )
}
