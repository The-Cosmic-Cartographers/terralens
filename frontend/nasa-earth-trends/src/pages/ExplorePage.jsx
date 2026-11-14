import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import VariableCard from '../components/VariableCard.jsx'
import { useData } from '../hooks/useData.js'

const lineupVariables = [
  {
    name: 'Air temperature',
    unit: '°C',
    kind: 'temperature',
    glyph: 'T°',
    source: 'MERRA-2 reanalysis',
    description: 'The warmth of the air near the surface, tracked over time.',
    significance: 'A foundational climate signal connected to heat stress and water demand.',
    variableId: 't2m',
  },
  {
    name: 'Soil moisture',
    unit: 'kg/m²',
    kind: 'moisture',
    glyph: '≈',
    source: 'MERRA-2 reanalysis',
    description: 'The amount of water held in the upper layer of soil.',
    significance: 'Connects rainfall to ecosystems, agriculture, evaporation, and drought.',
    variableId: 'soil_moisture_0_10cm',
  },
  {
    name: 'Precipitation',
    unit: 'mm/month',
    kind: 'rain',
    glyph: '∿',
    source: 'NASA precipitation product',
    description: 'Rain and other water arriving at the surface.',
    significance: 'Helps describe water availability and the balance between wet and dry seasons.',
    variableId: 'precipitation',
  },
  {
    name: 'Evapotranspiration',
    unit: 'mm/day',
    kind: 'evaporation',
    glyph: '↑',
    source: 'MERRA-2 reanalysis',
    description: 'Water moving back to the atmosphere from land and plants.',
    significance: 'Shows how heat, vegetation, and available water interact.',
    variableId: 'evapotranspiration',
  },
  {
    name: 'Aerosol optical depth',
    unit: 'unitless',
    kind: 'aerosol',
    glyph: '◌',
    source: 'NASA aerosol product',
    description: 'A measure of how much airborne particle haze blocks light.',
    significance: 'Can indicate dust, smoke, or pollution and influence incoming sunlight.',
    variableId: 'aerosol_optical_depth',
  },
]

function ExplorePage() {
  const { data, loading, error, mode } = useData('catalogue')
  const availableIds = new Set(data?.map((item) => item.variable_id))

  return (
    <div className="content-page lineup-page">
      <div className="page-heading lineup-heading">
        <div>
          <span className="section-index">02 / SIGNALS</span>
          <h1>The Lineup</h1>
          <p>
            Five environmental variables, read together across 1981–2025.
          </p>
        </div>
        <span className="period-chip">
          {mode === 'static' ? 'Static snapshot' : 'Live API'}
        </span>
      </div>

      <SampleDataWarning />

      <div className="lineup-intro">
        <p>
          No single measurement tells the whole story. These variables describe
          heat, water, atmosphere, and the exchange between land and air.
        </p>
        <span>Analysis window / 1981—2025</span>
      </div>

      {loading && <LoadingState label="Checking available variables" />}
      {error && <ErrorState message={error.message} />}

      <div className="lineup-grid">
        {lineupVariables.map((variable, index) => (
          <Link
            className="lineup-link-card"
            to={`/explore/${variable.variableId}`}
            key={variable.variableId}
          >
            <VariableCard variable={variable} index={index} />
            <span className="lineup-availability">
              {availableIds.has(variable.variableId)
                ? 'Catalogue entry available'
                : 'Result connection pending'}
            </span>
          </Link>
        ))}
      </div>

      {!loading && !error && data?.length === 0 && (
        <EmptyState
          title="No catalogue entries available"
          message="The variable guide is still visible, but the connected data catalogue is empty."
        />
      )}

      <section className="lineup-compare-note">
        <div>
          <span className="section-index">NO₂ / COMPARISON TRACK</span>
          <h2>Delhi ↔ Dublin</h2>
          <p>
            Nitrogen dioxide is reserved for the comparison view: a city-scale
            atmospheric signal that can help contrast two places without
            implying a cause.
          </p>
        </div>
        <ProductBadge type="satellite" />
      </section>
    </div>
  )
}

export default ExplorePage
