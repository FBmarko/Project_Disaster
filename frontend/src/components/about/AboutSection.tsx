import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

type AboutSectionProps = {
  id: string
  title: string
  icon: LucideIcon
  children: ReactNode
}

export function AboutSection({ id, title, icon: Icon, children }: AboutSectionProps) {
  const headingId = `${id}-heading`

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-2xl border border-border-subtle/70 bg-card p-5 shadow-sm sm:p-7"
    >
      <div className="mb-4 flex items-center gap-3">
        <span
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-red-soft text-brand-red-foreground"
          aria-hidden="true"
        >
          <Icon size={21} />
        </span>
        <h2 id={headingId} className="text-lg font-semibold tracking-tight text-text-primary sm:text-xl">
          {title}
        </h2>
      </div>
      <div className="space-y-3 text-sm leading-6 text-text-secondary sm:text-[15px] sm:leading-7">
        {children}
      </div>
    </section>
  )
}
