import { Link } from 'react-router-dom'

import DatasetTable from '../components/DatasetTable.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import KpiTile from '../components/KpiTile.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import VariableCard from '../components/VariableCard.jsx'
import { useData } from '../hooks/useData.js'

// Catalogue variable ids (see data/catalogue.json).
const guide = [
  {
    name: 'Air temperature',
    unit: '°C',
    glyph: 'T°',
    source: 'MERRA-2 reanalysis',
    description: 'The warmth of the air near the surface, tracked over time.',
    significance: 'A foundational climate signal connected to heat stress and water demand.',
    variableId: 't2m',
  },
  {
    name: 'Soil moisture',
    unit: 'kg/m²',
    glyph: '≈',
    source: 'GLDAS land model',
    description: 'The amount of water held in the upper layer of soil.',
    significance: 'Connects rainfall to ecosystems, agriculture, evaporation, and drought.',
    variableId: 'soil_moisture_0_10',
  },
  {
    name: 'Precipitation',
    unit: 'mm/month',
    glyph: '∿',
    source: 'GPM IMERG satellite estimate',
    description: 'Rain and other water arriving at the surface.',
    significance: 'Helps describe water availability and the balance between wet and dry seasons.',
    variableId: 'precipitation',
  },
  {
    name: 'Evapotranspiration',
    unit: 'mm/day',
    glyph: '↑',
    source: 'GLDAS land model',
    description: 'Water moving back to the atmosphere from land and plants.',
    significance: 'Shows how heat, vegetation, and available water interact.',
    variableId: 'evapotranspiration',
  },
  {
    name: 'Aerosol optical depth',
    unit: 'unitless',
    glyph: '◌',
    source: 'MERRA-2 reanalysis',
    description: 'A measure of how much airborne particle haze blocks light.',
    significance: 'Can indicate dust, smoke, or pollution and influence incoming sunlight.',
    variableId: 'aerosol',
  },
]

function ExplorePage() {
  const { data, loading, error, mode } = useData('catalogue')
  const items = data ?? []
  const status = new Map(items.map((item) => [item.variable_id, item.status]))
  const ready = items.filter((item) => item.status === 'ready').length

  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>The Lineup</h1>
          <p>
            Environmental variables read together across 1981–2025. No single
            measurement tells the whole story.
          </p>
        </div>
        <span className="chip">{mode === 'static' ? 'Static snapshot' : 'Live API'}</span>
      </div>

      <SampleDataWarning />

      <div className="kpi-row">
        <KpiTile label="In catalogue" value={data ? items.length : '—'} note="Datasets listed" />
        <KpiTile label="Ready" value={data ? ready : '—'} note="Results available" tone="blue" />
        <KpiTile
          label="Coming soon"
          value={data ? items.length - ready : '—'}
          note="Pull or analysis pending"
        />
        <KpiTile label="Window" value="1981–2025" note="Monthly series" />
      </div>

      {loading && <LoadingState label="Checking available variables" />}
      {error && <ErrorState message={error.message} />}

      <div className="grid">
        <Panel className="span-12" title="Catalogue" flush>
          <DatasetTable items={items} />
          {!loading && !error && items.length === 0 && (
            <EmptyState
              title="No catalogue entries available"
              message="The variable guide is below, but the connected data catalogue is empty."
            />
          )}
        </Panel>

        <Panel className="span-12" title="Variable guide">
          <div className="lineup-grid">
            {guide.map((variable, index) => (
              <Link
                className="lineup-link-card"
                to={`/explore/${variable.variableId}`}
                key={variable.variableId}
              >
                <VariableCard variable={variable} index={index} />
                <span className="lineup-availability">
                  {status.get(variable.variableId) === 'ready'
                    ? 'Result available'
                    : 'Result pending'}
                </span>
              </Link>
            ))}
          </div>
        </Panel>

        <Panel className="span-12 panel-accent" title="NO₂ comparison track" meta={<ProductBadge type="satellite" />}>
          <p>
            Delhi ↔ Dublin. Nitrogen dioxide is reserved for the comparison
            view: a city-scale atmospheric signal that can help contrast two
            places without implying a cause.
          </p>
        </Panel>
      </div>
    </div>
  )
}

export default ExplorePage
