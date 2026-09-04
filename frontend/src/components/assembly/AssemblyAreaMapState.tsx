import { LoaderCircle, MapPinned, TriangleAlert } from 'lucide-react'

export function AssemblyAreaMapState({ state }: { state: 'missing-key' | 'loading' | 'error' }) {
  const Icon = state === 'loading' ? LoaderCircle : state === 'error' ? TriangleAlert : MapPinned
  return (
    <div className="flex h-full w-full items-center justify-center bg-surface p-5 text-center" role={state === 'error' ? 'alert' : 'status'}>
      <div className="max-w-sm">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-border-subtle bg-card text-brand-red">
          <Icon size={26} aria-hidden="true" className={state === 'loading' ? 'motion-safe:animate-spin' : undefined} />
        </span>
        <p className="mt-4 font-semibold">{state === 'missing-key' ? 'Google Maps API anahtarı yapılandırılmamış.' : state === 'error' ? 'Google Maps yüklenemedi.' : 'Harita yükleniyor…'}</p>
        {state !== 'loading' ? <p className="mt-2 text-sm leading-6 text-text-secondary">Harita şu anda gösterilemiyor. Konum seçimiyle devam edebilirsiniz.</p> : null}
      </div>
    </div>
  )
}
