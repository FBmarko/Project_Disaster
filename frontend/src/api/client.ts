export class ApiError extends Error {
  readonly status: number | null
  constructor(status: number | null = null) {
    super('Project API request failed')
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Resolves an API path against an optional base URL.
 *
 * - If baseUrl is missing or empty: returns a same-origin relative path (e.g. '/api/v1/health').
 * - If baseUrl is configured: prefixes the normalized path (e.g. 'https://api.example.com/api/v1/health').
 * - Normalizes any trailing slashes from the base and ensures a single leading slash on the path.
 */
export function resolveApiUrl(path: string, baseUrl?: string | null): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const trimmedBase = baseUrl?.trim().replace(/\/+$/, '')
  if (!trimmedBase) {
    return normalizedPath
  }
  return `${trimmedBase}${normalizedPath}`
}

/** Never carry raw server errors (or location-bearing URLs) into the UI/logs. */
export async function getJson<T>(path: string, parse: (value: unknown) => T, signal: AbortSignal): Promise<T> {
  const url = resolveApiUrl(path, import.meta.env?.VITE_API_BASE_URL)
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.any([signal, AbortSignal.timeout(20_000)]),
    credentials: 'omit',
    cache: 'no-store',
    referrerPolicy: 'no-referrer',
  })
  if (!response.ok) throw new ApiError(response.status)
  return parse(await response.json() as unknown)
}
