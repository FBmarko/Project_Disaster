import { useCallback, useEffect, useState } from 'react'
import { LocateFixed } from 'lucide-react'
import { APIProvider, APILoadingStatus, AdvancedMarker, Map, Pin, useApiLoadingStatus, useMap } from '@vis.gl/react-google-maps'
import { DEVELOPMENT_MAP_ID, SIMULATION_MAP as TURKEY_MAP_VIEW } from '@/constants/simulation'
import { hasValidAssemblyCoordinates } from '@/utils/assemblyAreas'
import { useTheme } from '@/hooks/useTheme'
import type { AssemblyMapProps } from './AssemblyAreaMap'
import type { AssemblyArea, AssemblyCoordinates } from '@/types/assembly'
import { AssemblyAreaMapState } from './AssemblyAreaMapState'

let authenticationFailed = false

function MapFocus({ areas, selectedAreaId, userLocation, focusRequest }: AssemblyMapProps) {
  const map = useMap('assembly-map')
  const target = areas.find((area) => area.id === selectedAreaId) ?? userLocation
  const latitude = hasValidAssemblyCoordinates(target) ? target.latitude : null
  const longitude = hasValidAssemblyCoordinates(target) ? target.longitude : null
  const polygon = target && 'geometry' in target && target.geometry?.type === 'Polygon' ? target.geometry : null
  useEffect(() => {
    if (!map) return
    if (polygon) {
      const bounds = new google.maps.LatLngBounds()
      polygon.coordinates.forEach(ring => ring.forEach(([lng, lat]) => bounds.extend({ lat, lng })))
      map.fitBounds(bounds, 40)
    } else if (latitude !== null && longitude !== null) {
      map.panTo({ lat: latitude, lng: longitude })
      map.setZoom(15)
    } else {
      const { padding, ...bounds } = TURKEY_MAP_VIEW.bounds
      map.fitBounds(bounds, padding)
    }
  }, [map, latitude, longitude, polygon, focusRequest])
  return null
}

/** Preserve backend polygon rings; never guess a centroid or an entrance. */
function AssemblyPolygons({ areas, selectedAreaId, onSelect }: AssemblyMapProps) {
  const map = useMap('assembly-map')
  useEffect(() => {
    if (!map) return
    const polygons = areas.flatMap(area => {
      if (area.geometry?.type !== 'Polygon') return []
      const selected = area.id === selectedAreaId
      const polygon = new google.maps.Polygon({ map,
        paths: area.geometry.coordinates.map(ring => ring.map(([lng, lat]) => ({ lat, lng }))),
        strokeColor: selected ? '#991B1B' : '#EF2B2D', strokeWeight: selected ? 4 : 2,
        fillColor: '#EF2B2D', fillOpacity: selected ? 0.35 : 0.15,
      })
      const listener = polygon.addListener('click', () => onSelect(area.id))
      return [{ polygon, listener }]
    })
    return () => polygons.forEach(({ polygon, listener }) => { listener.remove(); polygon.setMap(null) })
  }, [map, areas, selectedAreaId, onSelect])
  return null
}

function MapScene(props: AssemblyMapProps & { loaderFailed: boolean }) {
  const { theme } = useTheme()
  const status = useApiLoadingStatus()
  const [authFailed, setAuthFailed] = useState(authenticationFailed)
  const [tilesReady, setTilesReady] = useState(false)
  const [timedOut, setTimedOut] = useState(false)
  const failed = props.loaderFailed || authFailed || timedOut || status === APILoadingStatus.FAILED || status === APILoadingStatus.AUTH_FAILURE

  useEffect(() => {
    const previous = window.gm_authFailure
    const handleFailure = () => { authenticationFailed = true; setAuthFailed(true); previous?.() }
    window.gm_authFailure = handleFailure
    return () => { if (window.gm_authFailure === handleFailure) window.gm_authFailure = previous }
  }, [])
  useEffect(() => {
    if (tilesReady || failed) return
    const timeout = window.setTimeout(() => setTimedOut(true), TURKEY_MAP_VIEW.loadTimeoutMs)
    return () => window.clearTimeout(timeout)
  }, [tilesReady, failed])

  if (failed) return <AssemblyAreaMapState state="error" />
  return (
    <>
      <Map id="assembly-map" defaultCenter={TURKEY_MAP_VIEW.center} defaultZoom={TURKEY_MAP_VIEW.zoom}
        defaultBounds={TURKEY_MAP_VIEW.bounds} mapId={import.meta.env.VITE_GOOGLE_MAPS_MAP_ID?.trim() || DEVELOPMENT_MAP_ID}
        colorScheme={theme === 'dark' ? 'DARK' : 'LIGHT'} mapTypeId="roadmap" gestureHandling="cooperative"
        streetViewControl={false} mapTypeControl={false} fullscreenControl={false}
        rotateControl={false} cameraControl={false} zoomControl clickableIcons={false}
        reuseMaps={false} onTilesLoaded={() => setTilesReady(true)}>
        <MapFocus {...props} />
        <AssemblyPolygons {...props} />
        {hasValidAssemblyCoordinates(props.userLocation) ? <AdvancedMarker
          position={{ lat: props.userLocation.latitude, lng: props.userLocation.longitude }} title="Kullanıcı Konumu">
          <span className="flex h-10 w-10 items-center justify-center rounded-full border-4 border-card bg-location text-white shadow-md">
            <LocateFixed size={23} aria-hidden="true" /><span className="sr-only">Kullanıcı Konumu</span>
          </span>
        </AdvancedMarker> : null}
        {props.areas.filter((area): area is AssemblyArea & AssemblyCoordinates => hasValidAssemblyCoordinates(area)).map((area) => {
          const selected = area.id === props.selectedAreaId
          return <AdvancedMarker key={area.id} position={{ lat: area.latitude, lng: area.longitude }}
            title={`${selected ? 'Seçili alan: ' : 'Toplanma Alanı: '}${area.name}`}
            onClick={() => props.onSelect(area.id)} zIndex={selected ? 2 : 1}>
            <Pin background={selected ? '#991B1B' : '#EF2B2D'} borderColor="#7F1D1D" glyphColor="#FFFFFF" glyph={selected ? '✓' : undefined} scale={selected ? 1.2 : 1} />
          </AdvancedMarker>
        })}
      </Map>
      {!tilesReady ? <div className="absolute inset-0"><AssemblyAreaMapState state="loading" /></div> : null}
    </>
  )
}

export default function GoogleAssemblyAreaMap(props: AssemblyMapProps & { apiKey: string }) {
  const [loaderFailed, setLoaderFailed] = useState(false)
  const onError = useCallback(() => setLoaderFailed(true), [])
  // Same wrapper/provider settings as SimulationPage. Never log external errors or key-bearing URLs.
  return <APIProvider apiKey={props.apiKey} version="quarterly" language="tr" region="TR"
    disableUsageAttribution solutionChannel="" onError={onError}>
    <MapScene {...props} loaderFailed={loaderFailed} />
  </APIProvider>
}
