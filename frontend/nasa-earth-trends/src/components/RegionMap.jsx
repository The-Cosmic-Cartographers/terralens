import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'

import 'maplibre-gl/dist/maplibre-gl.css'

const FALLBACK_CENTER = [20, 25]

function RegionMap({ region, regionData }) {
  const mapContainer = useRef(null)
  const map = useRef(null)

  useEffect(() => {
    if (!mapContainer.current || map.current) {
      return undefined
    }

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://tiles.openfreemap.org/styles/bright',
      center: region.center || FALLBACK_CENTER,
      zoom: region.zoom || 2.2,
      attributionControl: true,
    })

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right')

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [region.center, region.zoom])

  useEffect(() => {
    if (!map.current) {
      return
    }

    const selectedGeometry = regionData?.geometry
    const sourceId = 'selected-region'
    const layerId = 'selected-region-outline'

    const updateRegionLayer = () => {
      if (map.current.getLayer(layerId)) {
        map.current.removeLayer(layerId)
      }

      if (map.current.getSource(sourceId)) {
        map.current.removeSource(sourceId)
      }

      if (!selectedGeometry) {
        return
      }

      map.current.addSource(sourceId, {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: selectedGeometry,
        },
      })

      map.current.addLayer({
        id: layerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#8fb7ad',
          'line-width': 3,
          'line-opacity': 0.9,
        },
      })
    }

    if (map.current.isStyleLoaded()) {
      updateRegionLayer()
    } else {
      map.current.once('load', updateRegionLayer)
    }
  }, [regionData])

  return (
    <div className="region-map-shell">
      <div ref={mapContainer} className="region-map" />
      {!regionData?.geometry && (
        <div className="map-data-note">
          Region boundary will appear when its GeoJSON is available.
        </div>
      )}
      <div className="map-label">
        <span className="map-label-kicker">Selected field site</span>
        <strong>{region.name}</strong>
        <span>{region.shortLocation}</span>
      </div>
    </div>
  )
}

export default RegionMap
