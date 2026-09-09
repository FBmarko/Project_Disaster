import { useEffect, useMemo, useRef, useState } from 'react'
import Map, { Layer, Marker, NavigationControl, Source, type MapRef } from 'react-map-gl/maplibre'
import * as maplibregl from 'maplibre-gl'

import { LocateFixed } from 'lucide-react'
import {
  MAP_LOAD_TIMEOUT_MS,
  OPENFREEMAP_STYLE_URL,
  TURKEY_MAP_BOUNDS,
  TURKEY_MAP_CENTER,
  TURKEY_MAP_INITIAL_ZOOM,
} from '@/config/map'
import { hasValidAssemblyCoordinates } from '@/utils/assemblyAreas'
import type { AssemblyArea, AssemblyCoordinates } from '@/types/assembly'
import type { AssemblyMapProps } from './AssemblyAreaMap'
import { AssemblyAreaMapState } from './AssemblyAreaMapState'

function AssemblyPin({ selected, name }: { selected: boolean; name: string }) {
  return (
    <span
      role="img"
      aria-label={`${selected ? 'Seçili alan: ' : 'Toplanma Alanı: '}${name}`}
      title={`${selected ? 'Seçili alan: ' : 'Toplanma Alanı: '}${name}`}
      className={`inline-block transition-transform ${selected ? 'scale-125' : 'hover:scale-110'}`}
    >
      <svg
        width="28"
        height="36"
        viewBox="0 0 28 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="drop-shadow-md cursor-pointer"
      >
        <path
          d="M14 0C6.268 0 0 6.268 0 14c0 10.5 14 22 14 22s14-11.5 14-22c0-7.732-6.268-14-14-14z"
          fill={selected ? '#991B1B' : '#EF2B2D'}
          stroke="#7F1D1D"
          strokeWidth="2"
        />
        {selected ? (
          <text
            x="14"
            y="18"
            textAnchor="middle"
            fill="#FFFFFF"
            fontSize="12"
            fontWeight="bold"
          >
            ✓
          </text>
        ) : (
          <circle cx="14" cy="14" r="5" fill="#FFFFFF" />
        )}
      </svg>
    </span>
  )
}

export default function MapLibreAssemblyAreaMap(props: AssemblyMapProps) {
  const mapRef = useRef<MapRef>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  const target = props.areas.find((area) => area.id === props.selectedAreaId) ?? props.userLocation
  const latitude = hasValidAssemblyCoordinates(target) ? target.latitude : null
  const longitude = hasValidAssemblyCoordinates(target) ? target.longitude : null
  const polygon =
    target && 'geometry' in target && target.geometry?.type === 'Polygon'
      ? target.geometry
      : null

  // Camera focus effect matching area selection and focus requests
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded) return

    if (polygon) {
      let minLng = Infinity
      let maxLng = -Infinity
      let minLat = Infinity
      let maxLat = -Infinity
      polygon.coordinates.forEach((ring) => {
        ring.forEach(([lng, lat]) => {
          if (lng < minLng) minLng = lng
          if (lng > maxLng) maxLng = lng
          if (lat < minLat) minLat = lat
          if (lat > maxLat) maxLat = lat
        })
      })
      if (minLng <= maxLng && minLat <= maxLat) {
        map.fitBounds(
          [
            [minLng, minLat],
            [maxLng, maxLat],
          ],
          { padding: 40, duration: 800 },
        )
      }
    } else if (latitude !== null && longitude !== null) {
      map.flyTo({ center: [longitude, latitude], zoom: 15, duration: 800 })
    } else {
      map.fitBounds(TURKEY_MAP_BOUNDS, { padding: 24, duration: 800 })
    }
  }, [loaded, latitude, longitude, polygon, props.focusRequest])

  // Polygons GeoJSON data
  const polygonFeatures = useMemo(() => {
    return {
      type: 'FeatureCollection' as const,
      features: props.areas
        .filter(
          (
            area,
          ): area is AssemblyArea & {
            geometry: { type: 'Polygon'; coordinates: number[][][] }
          } => area.geometry?.type === 'Polygon',
        )
        .map((area) => ({
          type: 'Feature' as const,
          id: area.id,
          properties: {
            id: area.id,
            name: area.name,
            selected: area.id === props.selectedAreaId,
          },
          geometry: area.geometry,
        })),
    }
  }, [props.areas, props.selectedAreaId])

  useEffect(() => {
    if (loaded || failed) return
    const timeout = window.setTimeout(() => {
      if (!loaded) setFailed(true)
    }, MAP_LOAD_TIMEOUT_MS)
    return () => window.clearTimeout(timeout)
  }, [loaded, failed])

  if (failed) {
    return <AssemblyAreaMapState state="error" />
  }

  return (
    <div className="relative h-full w-full">
      <Map
        ref={mapRef}
        mapLib={maplibregl}
        id="assembly-map"
        initialViewState={{
          longitude: TURKEY_MAP_CENTER.longitude,
          latitude: TURKEY_MAP_CENTER.latitude,
          zoom: TURKEY_MAP_INITIAL_ZOOM,
          bounds: TURKEY_MAP_BOUNDS,
          fitBoundsOptions: { padding: 24 },
        }}
        mapStyle={OPENFREEMAP_STYLE_URL}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={['assembly-polygons-fill']}

        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        onClick={(event) => {
          const feature = event.features?.[0]
          if (feature && feature.layer?.id === 'assembly-polygons-fill') {
            const areaId = feature.properties?.id as string | undefined
            if (areaId) {
              props.onSelect(areaId)
            }
          }
        }}
      >
        <NavigationControl position="top-right" showCompass={false} />

        {/* Polygons source and layers */}
        <Source id="assembly-polygons" type="geojson" data={polygonFeatures}>
          <Layer
            id="assembly-polygons-fill"
            type="fill"
            paint={{
              'fill-color': '#EF2B2D',
              'fill-opacity': [
                'case',
                ['boolean', ['get', 'selected'], false],
                0.35,
                0.15,
              ],
            }}
          />
          <Layer
            id="assembly-polygons-line"
            type="line"
            paint={{
              'line-color': [
                'case',
                ['boolean', ['get', 'selected'], false],
                '#991B1B',
                '#EF2B2D',
              ],
              'line-width': [
                'case',
                ['boolean', ['get', 'selected'], false],
                4,
                2,
              ],
            }}
          />
        </Source>

        {/* User location marker */}
        {hasValidAssemblyCoordinates(props.userLocation) ? (
          <Marker
            longitude={props.userLocation.longitude}
            latitude={props.userLocation.latitude}
            anchor="center"
            style={{ zIndex: 3 }}
          >
            <span
              className="flex h-10 w-10 items-center justify-center rounded-full border-4 border-card bg-location text-white shadow-md"
              title="Kullanıcı Konumu"
              aria-label="Kullanıcı Konumu"
            >
              <LocateFixed size={23} aria-hidden="true" />
              <span className="sr-only">Kullanıcı Konumu</span>
            </span>
          </Marker>
        ) : null}

        {/* Point assembly area markers */}
        {props.areas
          .filter((area): area is AssemblyArea & AssemblyCoordinates =>
            hasValidAssemblyCoordinates(area),
          )
          .map((area) => {
            const selected = area.id === props.selectedAreaId
            return (
              <Marker
                key={area.id}
                longitude={area.longitude}
                latitude={area.latitude}
                anchor="bottom"
                style={{ zIndex: selected ? 2 : 1 }}
                onClick={(e) => {
                  e.originalEvent.stopPropagation()
                  props.onSelect(area.id)
                }}
              >
                <AssemblyPin selected={selected} name={area.name} />
              </Marker>
            )
          })}
      </Map>
      {!loaded ? (
        <div className="absolute inset-0 z-10 pointer-events-none">
          <AssemblyAreaMapState state="loading" />
        </div>
      ) : null}
    </div>
  )
}
