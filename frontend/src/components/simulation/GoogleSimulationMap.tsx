import { useCallback, useEffect, useState } from 'react'
import { APIProvider, APILoadingStatus, AdvancedMarker, Map, Pin, useApiLoadingStatus } from '@vis.gl/react-google-maps'
import { DEVELOPMENT_MAP_ID, SIMULATION_MAP } from '@/constants/simulation'
import type { SimulationLocation } from '@/types/simulation'
import { SimulationMapState } from './SimulationMapState'

type MapProps = {
  location: SimulationLocation | null
  onSelect: (location: SimulationLocation) => void
}

// Preserve an authentication failure across route changes until the page is reloaded.
let authenticationFailed = false

function MapScene({ location, onSelect, loaderFailed }: MapProps & { loaderFailed: boolean }) {
  const status = useApiLoadingStatus()
  const [authFailed, setAuthFailed] = useState(authenticationFailed)
  const [tilesReady, setTilesReady] = useState(false)
  const [timedOut, setTimedOut] = useState(false)
  const failed = loaderFailed || authFailed || timedOut || status === APILoadingStatus.FAILED || status === APILoadingStatus.AUTH_FAILURE

  useEffect(() => {
    // Google reports credential/billing/referrer failures through this documented hook.
    // It is registered in the child before APIProvider starts its loading effect.
    const previous = window.gm_authFailure
    const handleFailure = () => {
      authenticationFailed = true
      setAuthFailed(true)
      previous?.()
    }
    window.gm_authFailure = handleFailure
    return () => {
      if (window.gm_authFailure === handleFailure) window.gm_authFailure = previous
    }
  }, [])

  useEffect(() => {
    if (tilesReady || failed) return
    const timeout = window.setTimeout(() => setTimedOut(true), SIMULATION_MAP.loadTimeoutMs)
    return () => window.clearTimeout(timeout)
  }, [tilesReady, failed])

  if (failed) return <SimulationMapState state="error" />

  return (
    <>
      <Map defaultCenter={SIMULATION_MAP.center} defaultZoom={SIMULATION_MAP.zoom}
        defaultBounds={SIMULATION_MAP.bounds} mapId={import.meta.env.VITE_GOOGLE_MAPS_MAP_ID?.trim() || DEVELOPMENT_MAP_ID}
        colorScheme="LIGHT" mapTypeId="roadmap" gestureHandling="cooperative"
        streetViewControl={false} mapTypeControl={false} fullscreenControl={false}
        rotateControl={false} cameraControl={false} zoomControl={true} clickableIcons={false}
        reuseMaps onTilesLoaded={() => setTilesReady(true)} onClick={(event) => {
          const point = event.detail.latLng
          if (point) onSelect({ latitude: point.lat, longitude: point.lng })
        }}>
        {location ? <AdvancedMarker position={{ lat: location.latitude, lng: location.longitude }} title="Seçilen simülasyon konumu">
          <Pin background="#EF2B2D" borderColor="#B91C1C" glyphColor="#FFFFFF" />
        </AdvancedMarker> : null}
      </Map>
      {!tilesReady ? <div className="absolute inset-0"><SimulationMapState state="loading" /></div> : null}
    </>
  )
}

export default function GoogleSimulationMap(props: MapProps & { apiKey: string }) {
  const [loaderFailed, setLoaderFailed] = useState(false)
  // Never log provider errors: external messages/URLs can contain the API key.
  const onError = useCallback(() => setLoaderFailed(true), [])
  return (
    <APIProvider apiKey={props.apiKey} version="quarterly" language="tr" region="TR"
      disableUsageAttribution solutionChannel="" onError={onError}>
      <MapScene location={props.location} onSelect={props.onSelect} loaderFailed={loaderFailed} />
    </APIProvider>
  )
}
