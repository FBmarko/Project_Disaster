import { ExternalLink } from 'lucide-react'

type DataSourceCardProps = {
  title: string
  source: string
  sourceHref: string
  license: string
  licenseHref: string
  description: string
  attribution?: string
}

const linkClass =
  'inline-flex min-h-7 max-w-full items-center gap-1.5 font-medium text-text-primary underline decoration-border-subtle underline-offset-4 transition-colors hover:text-brand-red'

export function DataSourceCard({
  title,
  source,
  sourceHref,
  license,
  licenseHref,
  description,
  attribution,
}: DataSourceCardProps) {
  return (
    <article className="rounded-xl border border-border-subtle bg-surface/60 p-4 sm:p-5">
      <h3 className="font-semibold text-text-primary">{title}</h3>
      <p className="mt-2">{description}</p>
      {attribution ? <p className="mt-3 text-xs leading-5">{attribution}</p> : null}
      <dl className="mt-4 grid gap-3 border-t border-border-subtle pt-4 text-sm sm:grid-cols-[5rem_minmax(0,1fr)]">
        <dt className="font-medium text-text-secondary">Kaynak</dt>
        <dd className="min-w-0">
          <a href={sourceHref} target="_blank" rel="noreferrer" className={linkClass}>
            <span className="min-w-0 break-words">{source}</span>
            <ExternalLink size={14} className="shrink-0" aria-hidden="true" />
            <span className="sr-only"> (yeni sekmede açılır)</span>
          </a>
        </dd>
        <dt className="font-medium text-text-secondary">Lisans</dt>
        <dd className="min-w-0">
          <a href={licenseHref} target="_blank" rel="noreferrer" className={linkClass}>
            <span className="min-w-0 break-words">{license}</span>
            <ExternalLink size={14} className="shrink-0" aria-hidden="true" />
            <span className="sr-only"> (yeni sekmede açılır)</span>
          </a>
        </dd>
      </dl>
    </article>
  )
}
