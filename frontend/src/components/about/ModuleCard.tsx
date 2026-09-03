import type { LucideIcon } from 'lucide-react'

type ModuleCardProps = {
  icon: LucideIcon
  title: string
  description: string
  status?: string
}

export function ModuleCard({ icon: Icon, title, description, status }: ModuleCardProps) {
  return (
    <article className="rounded-xl border border-border-subtle bg-surface/60 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-card text-brand-red shadow-sm"
          aria-hidden="true"
        >
          <Icon size={19} />
        </span>
        {status ? (
          <span className="rounded-full border border-border-subtle bg-card px-2.5 py-1 text-xs font-medium text-text-secondary">
            {status}
          </span>
        ) : null}
      </div>
      <h3 className="mt-4 font-semibold text-text-primary">{title}</h3>
      <p className="mt-1.5">{description}</p>
    </article>
  )
}
