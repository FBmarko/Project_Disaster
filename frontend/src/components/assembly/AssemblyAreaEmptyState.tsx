import { MapPinned } from 'lucide-react'
import type { AssemblyAreaSearch } from '@/types/assembly'

export function AssemblyAreaEmptyState({ search }: { search: AssemblyAreaSearch | null }) {
  return (
    <div className="rounded-xl border border-dashed border-border-subtle bg-surface px-5 py-8 text-center" role="status" aria-live="polite" aria-atomic="true">
      <MapPinned size={28} aria-hidden="true" className="mx-auto text-text-secondary" />
      <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-text-secondary">
        {search
          ? 'Seçtiğiniz konum için doğrulanmış toplanma alanı bilgisi şu anda gösterilemiyor. Bu, bölgede toplanma alanı olmadığı anlamına gelmez. Güncel bilgileri resmî kaynaklardan kontrol edin.'
          : 'Toplanma alanlarını görüntülemek için konumunuzu kullanabilir veya bölge seçebilirsiniz.'}
      </p>
    </div>
  )
}
