import { useMemo, useState } from 'react'

import { useData } from '../hooks/useData.js'
import { regions } from '../data/regionOptions.js'
import Panel from './Panel.jsx'
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
    <>
      <Panel
        className="span-8"
        title="Study regions"
        flush
        meta={
          <div className="segmented" role="tablist" aria-label="Study region">
            {regions.map((region) => (
              <button
                key={region.id}
                type="button"
                role="tab"
                aria-selected={region.id === selectedId}
                className={region.id === selectedId ? 'seg active' : 'seg'}
                onClick={() => setSelectedId(region.id)}
              >
                {region.name.split(' (')[0]}
              </button>
            ))}
          </div>
        }
      >
        <RegionMap region={selectedRegion} regionData={selectedRegionData} />
      </Panel>

      <Panel className="span-4" title="Selected site">
        <h3 className="site-name">{selectedRegion.name}</h3>
        <p className="field-location">{selectedRegion.shortLocation}</p>
        <p className="site-signal">{selectedRegion.signal}</p>
        <dl className="kv">
          <div>
            <dt>Investigation window</dt>
            <dd>1981–2025</dd>
          </div>
          <div>
            <dt>Region id</dt>
            <dd className="num">{selectedRegion.id}</dd>
          </div>
          <div>
            <dt>Boundary source</dt>
            <dd>{selectedRegionData?.source || 'Pending'}</dd>
          </div>
          <div>
            <dt>Licence</dt>
            <dd>{selectedRegionData?.licence || 'Pending'}</dd>
          </div>
        </dl>
        <p className="panel-foot">
          The map is a geographic reference, not a result.
        </p>
      </Panel>
    </>
  )
}

export default RegionExplorer
