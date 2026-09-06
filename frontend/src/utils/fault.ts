/**
 * Truthful display naming for geological fault segments.
 *
 * Fallback priority:
 * 1. Source feature name (if non-empty)
 * 2. Segment name (if non-empty)
 * 3. Authoritative catalog identifier (e.g. "Fay Segmenti · EUR_TRCS372")
 * 4. Generic label ("Fay Segmenti")
 *
 * Never invents names or infers unverified regional fault system names.
 */
export function formatFaultDisplayName(params: {
  name?: string | null
  segmentName?: string | null
  catalogId?: string | null
}): string {
  const name = params.name?.trim()
  if (name) return name

  const segmentName = params.segmentName?.trim()
  if (segmentName) return segmentName

  const catalogId = params.catalogId?.trim()
  if (catalogId) return `Fay Segmenti · ${catalogId}`

  return 'Fay Segmenti'
}
