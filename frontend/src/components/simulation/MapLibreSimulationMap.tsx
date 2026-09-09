import { useEffect, useState } from 'react'
import Map, { Marker, NavigationControl } from 'react-map-gl/maplibre'
import * as maplibregl from 'maplibre-gl'

import {
  MAP_LOAD_TIMEOUT_MS,
  OPENFREEMAP_STYLE_URL,
  TURKEY_MAP_BOUNDS,
  TURKEY_MAP_CENTER,
  TURKEY_MAP_INITIAL_ZOOM,
} from '@/config/map'
import type { SimulationLocation } from '@/types/simulation'
import { SimulationMapState } from './SimulationMapState'

type MapProps = {
  location: SimulationLocation | null
  onSelect: (location: SimulationLocation) => void
}

function SimulationPin() {
  return (
    <svg
      width="32"
      height="42"
      viewBox="0 0 32 42"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Seçilen simülasyon konumu"
      className="drop-shadow-md cursor-pointer"
    >
      <path
        d="M16 0C7.163 0 0 7.163 0 16c0 12 16 26 16 26s16-14 16-26c0-8.837-7.163-16-16-16z"
        fill="#EF2B2D"
        stroke="#B91C1C"
        strokeWidth="2"
      />
      <circle cx="16" cy="16" r="6" fill="#FFFFFF" />
    </svg>
  )
}

export default function MapLibreSimulationMap({ location, onSelect }: MapProps) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (loaded || failed) return
    const timeout = window.setTimeout(() => {
      if (!loaded) setFailed(true)
    }, MAP_LOAD_TIMEOUT_MS)
    return () => window.clearTimeout(timeout)
  }, [loaded, failed])

  if (failed) {
    return <SimulationMapState state="error" />
  }

  return (
    <div className="relative h-full w-full">
      <Map
        mapLib={maplibregl}
        initialViewState={{
          longitude: TURKEY_MAP_CENTER.longitude,
          latitude: TURKEY_MAP_CENTER.latitude,
          zoom: TURKEY_MAP_INITIAL_ZOOM,
          bounds: TURKEY_MAP_BOUNDS,
          fitBoundsOptions: { padding: 24 },
        }}
        mapStyle={OPENFREEMAP_STYLE_URL}
        style={{ width: '100%', height: '100%' }}
        cursor="crosshair"
        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        onClick={(event) => {
          const { lng, lat } = event.lngLat
          onSelect({ latitude: lat, longitude: lng })
        }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        {location ? (
          <Marker
            longitude={location.longitude}
            latitude={location.latitude}
            anchor="bottom"
            aria-label="Seçilen simülasyon konumu"
          >
            <SimulationPin />
          </Marker>
        ) : null}
      </Map>
      {!loaded ? (
        <div className="absolute inset-0 z-10 pointer-events-none">
          <SimulationMapState state="loading" />
        </div>
      ) : null}
    </div>
  )
}
