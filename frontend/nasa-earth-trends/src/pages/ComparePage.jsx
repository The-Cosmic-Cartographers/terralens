import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'

function ComparePage() {
  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>Opposite Trends</h1>
          <p>One variable. Two places. A more useful question.</p>
        </div>
        <ProductBadge type="satellite" />
      </div>

      <SampleDataWarning />

      <div className="kpi-row">
        <div className="kpi">
          <span className="kpi-label">Variable</span>
          <strong className="kpi-text">Nitrogen dioxide (NO₂)</strong>
        </div>
        <div className="kpi">
          <span className="kpi-label">Place A</span>
          <strong className="kpi-text">Delhi</strong>
        </div>
        <div className="kpi">
          <span className="kpi-label">Place B</span>
          <strong className="kpi-text">Dublin</strong>
        </div>
        <div className="kpi">
          <span className="kpi-label">Window</span>
          <strong className="kpi-text">1981–2025</strong>
        </div>
      </div>

      <div className="grid">
        <Panel className="span-8" title="Comparison result">
          <EmptyState
            title="Comparison result not connected yet"
            message="The backend model defines CompareResult, but its route and NO₂ result data are not available yet. The comparison frame is ready for the supplied analysis output."
            action={
              <Link className="button button-secondary" to="/explore">
                Review the Lineup
              </Link>
            }
          />
        </Panel>
        <Panel className="span-4" title="Why this comparison?">
          <p>
            Nitrogen dioxide is an atmospheric pollutant measured by satellite
            instruments. Comparing two regions can reveal different observed
            patterns, but the result cannot by itself explain why those
            patterns occurred.
          </p>
        </Panel>
      </div>
    </div>
  )
}

export default ComparePage
