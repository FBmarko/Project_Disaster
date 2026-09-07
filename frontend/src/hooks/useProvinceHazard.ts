import { useEffect, useState } from 'react'
import { getProvinceHazards } from '@/api/hazard'
import type { ProvinceHazardCollection } from '@/types/hazard'

export type UseProvinceHazardResult = {
  readonly data: ProvinceHazardCollection | null
  readonly isLoading: boolean
  readonly error: string | null
}

/**
 * Hook providing live province-level seismic hazard data from the backend.
 *
 * Connects to the Vite-proxied `/api/v1/earthquake-hazards/provinces` endpoint.
 * Exposes clean loading and error states without synthetic mock fallback.
 */
export function useProvinceHazard(): UseProvinceHazardResult {
  const [data, setData] = useState<ProvinceHazardCollection | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    getProvinceHazards(controller.signal)
      .then((collection) => {
        setData(collection)
        setError(null)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setData(null)
        setError('Deprem tehlikesi verileri şu anda yüklenemedi.')
        console.warn('Province hazard fetch failed:', err)
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [])

  return { data, isLoading, error }
}
