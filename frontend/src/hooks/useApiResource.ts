import { useEffect, useState } from 'react'

export type ApiState<T> = { status: 'idle' | 'loading' | 'error'; data?: never } | { status: 'success'; data: T }

/** Keyed results prevent even a single render of data from an old selection. */
export function useApiResource<T>(key: string | null, loader: (signal: AbortSignal) => Promise<T>): ApiState<T> {
  const [result, setResult] = useState<{ key: string; state: ApiState<T> } | null>(null)
  useEffect(() => {
    if (key === null) return
    const controller = new AbortController()
    Promise.resolve().then(() => loader(controller.signal)).then(data => {
      if (!controller.signal.aborted) setResult({ key, state: { status: 'success', data } })
    }).catch(() => {
      if (!controller.signal.aborted) setResult({ key, state: { status: 'error' } })
    })
    return () => controller.abort()
  }, [key, loader])
  if (key === null) return { status: 'idle' }
  return result?.key === key ? result.state : { status: 'loading' }
}
