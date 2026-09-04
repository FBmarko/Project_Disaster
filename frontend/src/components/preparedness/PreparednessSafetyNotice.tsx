import { ShieldCheck } from 'lucide-react'

export function PreparednessSafetyNotice() {
  return (
    <aside aria-label="Güvenlik hatırlatması" className="flex items-start gap-3 rounded-xl bg-surface p-4 text-xs leading-6 text-text-secondary">
      <ShieldCheck size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
      <p>Bu rehber genel hazırlık ve farkındalık amacıyla sunulmaktadır. Afet ve acil durumlarda AFAD ve ilgili resmî kurumların açıklama ve talimatlarını takip edin.</p>
    </aside>
  )
}
