import { useEffect, useRef, useState } from 'react'
import type { AssemblyCoordinates, AssemblyLocationStatus } from '@/types/assembly'
import { requestAssemblyLocation } from '@/utils/assemblyGeolocation'

export function useAssemblyLocation(onLocation: (location: AssemblyCoordinates) => void) {
  const [status, setStatus] = useState<AssemblyLocationStatus>('idle')
  const cancelRef = useRef<(() => void) | null>(null)
  useEffect(() => () => cancelRef.current?.(), [])

  function cancel() {
    cancelRef.current?.()
    setStatus('idle')
  }

  function request() {
    cancelRef.current?.()
    cancelRef.current = requestAssemblyLocation(navigator.geolocation, { onStatus: setStatus, onLocation })
  }

  return { status, request, cancel }
}
