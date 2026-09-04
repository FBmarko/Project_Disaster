import type { LucideIcon } from 'lucide-react'

export function GuideSection({ id, title, icon: Icon, items }: {
  id: string
  title: string
  icon: LucideIcon
  items: readonly string[] | null
}) {
  return (
    <section aria-labelledby={id} className="min-w-0 rounded-xl border border-border-subtle p-4 sm:p-5">
      <h3 id={id} className="flex items-center gap-3 text-sm font-semibold">
        <Icon size={20} aria-hidden="true" className="shrink-0 text-text-secondary" />{title}
      </h3>
      {items?.length ? (
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 wrap-anywhere text-text-primary marker:text-brand-red">
          {items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
        </ul>
      ) : <p className="mt-2 text-sm leading-6 text-text-secondary">
        {items === null ? 'Rehberiniz oluştuğunda burada yer alacak.' : 'Bu bölüm için öneri bulunmuyor.'}
      </p>}
    </section>
  )
}
