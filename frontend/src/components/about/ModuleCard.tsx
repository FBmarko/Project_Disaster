import type { LucideIcon } from 'lucide-react'

type ModuleCardProps = {
  icon: LucideIcon
  title: string
  description: string
  className?: string
}

export function ModuleCard({ icon: Icon, title, description, className = '' }: ModuleCardProps) {
  return (
    <article className={`min-w-0 rounded-xl border border-border-subtle bg-surface/60 p-4 sm:p-5 ${className}`}>
      <span
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-card text-brand-red shadow-sm"
        aria-hidden="true"
      >
        <Icon size={19} />
      </span>
      <h3 className="mt-4 font-semibold text-text-primary">{title}</h3>
      <p className="mt-1.5">{description}</p>
    </article>
  )
}
