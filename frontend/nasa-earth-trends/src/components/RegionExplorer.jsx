import { useMemo, useState } from 'react'

import { useData } from '../hooks/useData.js'
import { regions } from '../data/regionOptions.js'
import RegionMap from './RegionMap.jsx'

function RegionExplorer() {
  const [selectedId, setSelectedId] = useState(regions[0].id)
  const { data: apiRegions } = useData('regions')
  const selectedRegion = regions.find((region) => region.id === selectedId)
  const selectedRegionData = useMemo(
    () => apiRegions?.find((region) => region.region_id === selectedId),
    [apiRegions, selectedId],
  )

  return (
    <section className="fieldwork-section" id="fieldwork">
      <div className="section-heading-row">
        <div>
          <span className="section-index">01 / FIELD SITE</span>
          <h2>Start with a place.</h2>
          <p>
            Choose one of the five study regions. The map is a geographic
            reference—not a result.
          </p>
        </div>

        <label className="region-select-wrap">
          <span>Study region</span>
          <select
            value={selectedId}
            onChange={(event) => setSelectedId(event.target.value)}
          >
            {regions.map((region) => (
              <option key={region.id} value={region.id}>
                {region.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="fieldwork-grid">
        <RegionMap
          region={selectedRegion}
          regionData={selectedRegionData}
        />

        <div className="field-note">
          <span className="note-index">FIELD NOTE / {selectedRegion.id}</span>
          <h3>{selectedRegion.name}</h3>
          <p className="field-location">{selectedRegion.shortLocation}</p>
          <p>{selectedRegion.signal}</p>
          <div className="field-metadata">
            <div>
              <span>Investigation window</span>
              <strong>1981–2025</strong>
            </div>
            <div>
              <span>Boundary source</span>
              <strong>
                {selectedRegionData?.source || 'GeoJSON integration pending'}
              </strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default RegionExplorer
