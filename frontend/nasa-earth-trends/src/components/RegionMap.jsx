import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'

import { regions } from '../data/regionOptions.js'
import 'maplibre-gl/dist/maplibre-gl.css'

const FALLBACK_CENTER = [20, 25]

// Every study box is green; the selected one is red. Colours are literals
// because MapLibre paint expressions cannot read CSS custom properties.
const REGION_FILL = '#3fa66c'
const REGION_LINE = '#25784c'
const SELECTED_FILL = '#e45b52'
const SELECTED_LINE = '#a93635'

function RegionMap({ region, regionData, onRegionSelect }) {
  const mapContainer = useRef(null)
  const map = useRef(null)
  const [localFeatures, setLocalFeatures] = useState([])

  useEffect(() => {
    const controller = new AbortController()

    Promise.all(regions.map((item) => (
      fetch(`/data/regions/${item.id}.geojson`, { signal: controller.signal })
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null)
    )))
      .then((features) => setLocalFeatures(features.filter(Boolean)))
      .catch(() => setLocalFeatures([]))

    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!mapContainer.current || map.current) return undefined

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
    if (!map.current) return undefined

    const sourceId = 'study-regions'
    const fillLayerId = 'study-regions-fill'
    const lineLayerId = 'study-regions-line'
    const isSelected = ['==', ['get', 'region_id'], region.id]
    const selectedGeometry = regionData?.geometry
      || localFeatures.find((feature) => feature.properties?.region_id === region.id)?.geometry

    const updateRegionLayers = () => {
      if (map.current.getLayer(lineLayerId)) map.current.removeLayer(lineLayerId)
      if (map.current.getLayer(fillLayerId)) map.current.removeLayer(fillLayerId)
      if (map.current.getSource(sourceId)) map.current.removeSource(sourceId)

      const features = localFeatures.map((feature) => ({
        ...feature,
        properties: { ...feature.properties, region_id: feature.properties?.region_id },
      }))
      if (!features.some((feature) => feature.properties?.region_id === region.id) && selectedGeometry) {
        features.push({
          type: 'Feature',
          properties: { region_id: region.id },
          geometry: selectedGeometry,
        })
      }
      if (!features.length) return

      map.current.addSource(sourceId, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features },
      })
      map.current.addLayer({
        id: fillLayerId,
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': ['case', isSelected, SELECTED_FILL, REGION_FILL],
          'fill-opacity': ['case', isSelected, 0.3, 0.16],
        },
      })
      map.current.addLayer({
        id: lineLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': ['case', isSelected, SELECTED_LINE, REGION_LINE],
          'line-width': ['case', isSelected, 2.5, 1.4],
          'line-opacity': ['case', isSelected, 0.95, 0.7],
        },
      })
      map.current.on('click', fillLayerId, (event) => {
        const clickedId = event.features?.[0]?.properties?.region_id
        if (clickedId) onRegionSelect?.(clickedId)
      })
      map.current.on('mouseenter', fillLayerId, () => { map.current.getCanvas().style.cursor = 'pointer' })
      map.current.on('mouseleave', fillLayerId, () => { map.current.getCanvas().style.cursor = '' })
    }

    if (map.current.isStyleLoaded()) updateRegionLayers()
    else map.current.once('load', updateRegionLayers)

    return () => {
      map.current?.off('click', fillLayerId)
      map.current?.off('mouseenter', fillLayerId)
      map.current?.off('mouseleave', fillLayerId)
    }
  }, [localFeatures, region.id, regionData, onRegionSelect])

  return (
    <div className="region-map-shell">
      <div ref={mapContainer} className="region-map" />
      {!regionData?.geometry && !localFeatures.length && (
        <div className="map-data-note">Region boundary will appear when its GeoJSON is available.</div>
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
