import { ShieldCheck } from 'lucide-react'

export function AssemblyAreaSafetyNotice() {
  return (
    <aside aria-label="Resmî bilgi hatırlatması" className="flex items-start gap-3 rounded-2xl border border-border-subtle bg-card p-5 text-sm leading-7 text-text-secondary shadow-sm">
      <ShieldCheck size={22} aria-hidden="true" className="mt-1 shrink-0" />
      <p>Toplanma alanı bilgilerini afet öncesinde kontrol edin. Acil durumlarda AFAD ve ilgili resmî kurumların güncel açıklama ve yönlendirmelerini takip edin.</p>
    </aside>
  )
}
