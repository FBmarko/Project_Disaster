export class ApiError extends Error {
  readonly status: number | null
  constructor(status: number | null = null) {
    super('Project API request failed')
    this.name = 'ApiError'
    this.status = status
  }
}

/** Never carry raw server errors (or location-bearing URLs) into the UI/logs. */
export async function getJson<T>(path: string, parse: (value: unknown) => T, signal: AbortSignal): Promise<T> {
  const base = import.meta.env?.VITE_API_BASE_URL?.trim().replace(/\/$/, '')
  if (!base) throw new ApiError()
  const response = await fetch(`${base}${path}`, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.any([signal, AbortSignal.timeout(20_000)]),
    credentials: 'omit',
    cache: 'no-store',
    referrerPolicy: 'no-referrer',
  })
  if (!response.ok) throw new ApiError(response.status)
  return parse(await response.json() as unknown)
}
