import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import DatasetTable from '../components/DatasetTable.jsx'
import DropdownMenu from '../components/DropdownMenu.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import KpiTile from '../components/KpiTile.jsx'
import LineupRow from '../components/LineupRow.jsx'
import LineupSkeleton from '../components/LineupSkeleton.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import VariableCard from '../components/VariableCard.jsx'
import { regions } from '../data/regionOptions.js'
import { useData } from '../hooks/useData.js'
import { useWindowedLineups } from '../hooks/useWindowedLineups.js'
import { useWindow } from '../state/window.js'

const guide = [
  {
    name: 'Air temperature',
    datasetId: 'merra2_m2tmnxslv',
    unit: '°C',
    glyph: 'T°',
    source: 'MERRA-2 reanalysis',
    description: 'The warmth of the air near the surface, tracked over time.',
    significance: 'A foundational climate signal connected to heat stress and water demand.',
    variableId: 't2m',
  },
  {
    name: 'Soil moisture',
    datasetId: 'merra2_m2tmnxlnd_sfmc_v5_12_4',
    unit: 'm³/m³',
    glyph: '≈',
    source: 'MERRA-2 model reanalysis',
    description: 'The amount of water held in the upper layer of soil.',
    significance: 'Connects rainfall to ecosystems, agriculture, evaporation, and drought.',
    variableId: 'soil_moisture_0_5',
  },
  {
    name: 'Precipitation',
    datasetId: 'merra2_m2tmnxflx_prectotcorr_v5_12_4',
    unit: 'mm/month',
    glyph: '∇',
    source: 'MERRA-2 model reanalysis (bias-corrected)',
    description: 'Rain and other water arriving at the surface.',
    significance: 'Helps describe water availability and the balance between wet and dry seasons.',
    variableId: 'precipitation',
  },
  {
    name: 'Evapotranspiration',
    datasetId: 'merra2_m2tmnxlnd_evland_v5_12_4',
    unit: 'mm/day',
    glyph: '↑',
    source: 'MERRA-2 model reanalysis (land)',
    description: 'Water moving back to the atmosphere from land and plants.',
    significance: 'Shows how heat, vegetation, and available water interact.',
    variableId: 'evapotranspiration',
  },
  {
    name: 'Aerosol optical depth',
    datasetId: 'merra2_m2tmnxaer_v5_12_4',
    unit: 'unitless',
    glyph: '◉',
    source: 'MERRA-2 reanalysis',
    description: 'A measure of how much airborne particle haze blocks light.',
    significance: 'Can indicate dust, smoke, or pollution and influence incoming sunlight.',
    variableId: 'aerosol',
  },
]

function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [regionId, setRegionId] = useState(searchParams.get('region') || regions[0].id)
  const { data: catalogue, loading: catalogueLoading, error: catalogueError } = useData('catalogue')
  const { data: lineup, loading: lineupLoading, error: lineupError } = useData('lineup', { regionId })
  const { maxYear } = useWindow()
  const lineupList = useMemo(() => [lineup], [lineup])
  const { lineups: [windowedLineup], pending: windowPending, startYear, endYear } = useWindowedLineups(lineupList)
  const items = catalogue ?? []
  const rows = windowedLineup?.rows ?? []
  const isWindowed = Boolean(windowedLineup?.windowed)
  const selectedVariableId = searchParams.get('variable')
  const requestedStart = searchParams.get('start')
  const requestedEnd = searchParams.get('end')
  const visibleRows = selectedVariableId
    ? rows.filter((row) => row.variable_id === selectedVariableId)
    : rows
  const ready = items.filter((item) => item.status === 'ready').length

  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>The Lineup</h1>
          <p>Ranked environmental signals across the selected region, using supplied results from {startYear}–{endYear} (each row shows its own period).</p>
        </div>
      </div>

      <SampleDataWarning />

      <div className="kpi-row">
        <KpiTile label="In catalogue" value={catalogue ? items.length : '—'} note="Datasets listed" />
        <KpiTile label="Ready" value={catalogue ? ready : '—'} note="Results available" tone="blue" />
        <KpiTile label="Window" value={`${startYear}–${endYear}`} note="Monthly series" />
      </div>

      {catalogueError && <ErrorState message={catalogueError.message} />}
      {lineupError && <ErrorState message={lineupError.message} />}

      <div className="grid">
        <Panel className="span-12" title="Regional Lineup" flush>
          <div className="lineup-toolbar">
            <p>Choose a study region to inspect its ranked variables.</p>
            <DropdownMenu
              label="Study region"
              value={regionId}
              options={regions.map((region) => ({ value: region.id, label: region.name }))}
              onChange={(nextRegionId) => {
                setRegionId(nextRegionId)
                setSearchParams({
                  region: nextRegionId,
                  ...(selectedVariableId ? { variable: selectedVariableId } : {}),
                  ...(requestedStart ? { start: requestedStart } : {}),
                  ...(requestedEnd ? { end: requestedEnd } : {}),
                })
              }}
            />
          </div>
          {selectedVariableId && (
            <p className="filter-note">Showing the requested signal when the selected region has a supplied result. {requestedStart && requestedEnd ? `Requested window: ${requestedStart}–${requestedEnd}. ` : ''}<Link to={`/explore/${selectedVariableId}?region=${regionId}`}>Open its detail view.</Link></p>
          )}
          {isWindowed && !lineupLoading && !windowPending && (
            <p className="filter-note">
              Showing the supplied results for {startYear}–{endYear}. Each row starts at its own
              record start (air temperature begins in 1981) and rows are ranked by their adjusted
              p-value for this window. Choose {maxYear} in the header for the full record.
            </p>
          )}
          {lineupLoading || windowPending ? (
            <LineupSkeleton rows={selectedVariableId ? 1 : 5} label="Loading supplied environmental results" />
          ) : visibleRows.length ? (
            <div className="lineup-result-list">
              {visibleRows.map((row, index) => <LineupRow key={`${row.dataset_id}-${row.variable_id}`} row={row} rank={index + 1} />)}
            </div>
          ) : !lineupError && (
            <EmptyState
              title="No ranked results supplied for this region"
              message="The interface will show the lineup when the API or static result package provides it."
            />
          )}
        </Panel>

        <Panel className="span-12" title="Catalogue" flush>
          {catalogueLoading ? <LoadingState label="Loading the dataset catalogue" /> : <DatasetTable items={items} />}
          {!catalogueLoading && !catalogueError && items.length === 0 && (
            <EmptyState title="No catalogue entries available" message="The connected data catalogue is empty." />
          )}
        </Panel>

        <Panel className="span-12" title="Variable guide">
          <div className="lineup-grid">
            {guide.map((variable, index) => (
              <VariableCard
                key={variable.variableId}
                variable={variable}
                index={index}
                href={`/explore/${variable.variableId}?region=${regionId}`}
              />
            ))}
          </div>
        </Panel>

        <Panel className="span-12 panel-accent" title="NO₂ comparison track" meta={<ProductBadge type="satellite" />}>
          <p>Delhi ↔ Dublin. Nitrogen dioxide is reserved for the comparison view: a city-scale atmospheric signal that can contrast two places without implying a cause.</p>
        </Panel>
      </div>
    </div>
  )
}

export default ExplorePage
