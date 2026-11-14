import { Link } from 'react-router-dom'

import RegionExplorer from '../components/RegionExplorer.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import VariableCard from '../components/VariableCard.jsx'

const variables = [
  {
    name: 'Air temperature',
    unit: '°C',
    kind: 'temperature',
    glyph: 'T°',
    source: 'MERRA-2 reanalysis',
    description: 'The warmth of the air near the surface, tracked over time.',
    significance:
      'Temperature is a foundational climate signal. Persistent change can alter water demand, growing conditions, and heat stress.',
  },
  {
    name: 'Soil moisture',
    unit: 'kg/m²',
    kind: 'moisture',
    glyph: '≈',
    source: 'MERRA-2 reanalysis',
    description: 'The amount of water held in the upper layer of soil.',
    significance:
      'Soil moisture connects rainfall to ecosystems, agriculture, evaporation, and drought conditions.',
  },
  {
    name: 'Precipitation',
    unit: 'mm/month',
    kind: 'rain',
    glyph: '∿',
    source: 'NASA precipitation product',
    description: 'Rain and other water arriving at the surface.',
    significance:
      'Changes in precipitation can shift water availability, flood exposure, and the balance between wet and dry seasons.',
  },
  {
    name: 'Evapotranspiration',
    unit: 'mm/day',
    kind: 'evaporation',
    glyph: '↑',
    source: 'MERRA-2 reanalysis',
    description: 'Water moving back to the atmosphere from land and plants.',
    significance:
      'It helps describe how heat, vegetation, and available water interact across a landscape.',
  },
  {
    name: 'Aerosol optical depth',
    unit: 'unitless',
    kind: 'aerosol',
    glyph: '◌',
    source: 'NASA aerosol product',
    description: 'A measure of how much airborne particle haze blocks light.',
    significance:
      'Aerosols can indicate dust, smoke, or pollution and influence visibility and incoming sunlight.',
  },
]

function HomePage() {
  return (
    <div className="landing-page">
      <section className="observatory-hero">
        <div className="hero-copy-block">
          <span className="eyebrow">
            <span className="eyebrow-line" />
            TerraLens / Earth system investigation desk
          </span>
          <h1>
            Read the Earth
            <br />
            <span className="hero-emphasis">as a system.</span>
          </h1>
          <p className="hero-copy">
            A careful way to investigate long-term environmental change. Pick a
            place, inspect the signals, and follow the evidence back to its
            source.
          </p>
          <div className="hero-actions">
            <a className="button button-primary" href="#fieldwork">
              Choose a field site <span>↓</span>
            </a>
            <Link className="text-link" to="/case-files">
              How to read a case file <span>→</span>
            </Link>
          </div>
        </div>

        <div className="hero-instrument" aria-label="TerraLens investigation window">
          <div className="instrument-ring ring-large" />
          <div className="instrument-ring ring-small" />
          <div className="instrument-crosshair" />
          <div className="instrument-readout">
            <span>WINDOW</span>
            <strong>1981—2025</strong>
            <small>precomputed observations</small>
          </div>
          <div className="instrument-caption">ORBITAL VIEW / 01</div>
        </div>
      </section>

      <SampleDataWarning />

      <RegionExplorer />

      <section className="signal-section" id="signals">
        <div className="section-heading-row">
          <div>
            <span className="section-index">02 / SIGNALS</span>
            <h2>What are we looking for?</h2>
            <p>
              The Lineup puts five environmental variables side by side. The
              page will show supplied trends—not calculate them in the browser.
            </p>
          </div>
          <Link className="text-link" to="/explore">
            Open full Lineup →
          </Link>
        </div>

        <div className="variable-grid">
          {variables.map((variable, index) => (
            <VariableCard
              key={variable.name}
              variable={variable}
              index={index}
            />
          ))}
        </div>
      </section>

      <section className="comparison-callout">
        <div>
          <span className="section-index">03 / CONTRAST</span>
          <h2>One atmosphere. Two stories.</h2>
          <p>
            A dedicated comparison will place nitrogen dioxide over Delhi and
            Dublin side by side, once the comparison result is available from
            the analysis pipeline.
          </p>
        </div>
        <Link className="button button-light" to="/compare">
          Open Opposite Trends <span>↗</span>
        </Link>
      </section>

      <section className="trust-section">
        <span className="section-index">04 / METHOD</span>
        <div className="trust-grid">
          <div>
            <h2>Trust is part of the interface.</h2>
          </div>
          <div>
            <p>
              TerraLens labels the product type, analysis period, data
              coverage, method, limitations, and provenance for every result.
              It describes what the data shows over the measured period. It
              does not forecast or claim causes.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default HomePage
