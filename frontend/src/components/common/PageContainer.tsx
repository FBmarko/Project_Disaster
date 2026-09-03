import type { ReactNode } from 'react'

type PageContainerProps = {
  title: string
  description?: string
  children?: ReactNode
}

/** Standard page frame: centered white card with a heading. */
export function PageContainer({
  title,
  description,
  children,
}: PageContainerProps) {
  return (
    <section className="mx-auto w-full max-w-6xl rounded-2xl border border-border-subtle/70 bg-card p-5 shadow-sm sm:p-8">
      <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
        {title}
      </h1>

      {description ? (
        <p className="mt-2 max-w-2xl text-sm text-text-secondary sm:text-base">
          {description}
        </p>
      ) : null}

      {children ? <div className="mt-6">{children}</div> : null}
    </section>
  )
}
