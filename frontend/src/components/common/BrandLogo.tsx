import { Activity } from 'lucide-react'
import { useState } from 'react'
import logoUrl from '@/assets/brand/afet360-logo.png'

type BrandLogoProps = {
  /** Rendered height of the logo in pixels. */
  height?: number
  className?: string
}

/**
 * AFET360 wordmark.
 *
 * Renders the provided brand asset. If the asset is missing or fails to load,
 * falls back to an icon + text lockup so the UI never breaks.
 */
export function BrandLogo({ height = 32, className }: BrandLogoProps) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <span
        className={`inline-flex items-center gap-2 ${className ?? ''}`}
        style={{ height }}
      >
        <Activity
          className="text-brand-red-foreground"
          size={Math.round(height * 0.75)}
          aria-hidden="true"
        />
        <span
          className="font-bold tracking-tight text-text-primary"
          style={{ fontSize: Math.round(height * 0.68) }}
        >
          AFET<span className="text-brand-red-foreground">360</span>
        </span>
      </span>
    )
  }

  return (
    <img
      src={logoUrl}
      alt="AFET360"
      height={height}
      style={{ height }}
      className={`w-auto select-none rounded-sm bg-logo-surface ${className ?? ''}`}
      onError={() => setFailed(true)}
      draggable={false}
    />
  )
}
