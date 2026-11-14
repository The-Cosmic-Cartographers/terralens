import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'

function ComparePage() {
  return (
    <div className="content-page comparison-page">
      <div className="page-heading">
        <div>
          <span className="section-index">03 / CONTRAST</span>
          <h1>Opposite Trends</h1>
          <p>One variable. Two places. A more useful question.</p>
        </div>
        <ProductBadge type="satellite" />
      </div>

      <SampleDataWarning />

      <section className="comparison-panel">
        <div className="comparison-control">
          <span>Variable</span>
          <strong>Nitrogen dioxide (NO₂)</strong>
        </div>
        <div className="comparison-control">
          <span>Place A</span>
          <strong>Delhi</strong>
        </div>
        <div className="comparison-control">
          <span>Place B</span>
          <strong>Dublin</strong>
        </div>
        <div className="comparison-control">
          <span>Window</span>
          <strong>1981—2025</strong>
        </div>
      </section>

      <div className="comparison-explanation">
        <span className="section-index">WHY THIS COMPARISON?</span>
        <p>
          Nitrogen dioxide is an atmospheric pollutant measured by satellite
          instruments. Comparing two regions can reveal different observed
          patterns, but the result cannot by itself explain why those patterns
          occurred.
        </p>
      </div>

      <EmptyState
        title="Comparison result not connected yet"
        message="The backend model defines CompareResult, but its route and NO₂ result data are not available yet. The comparison frame is ready for the supplied analysis output."
        action={
          <Link className="button button-secondary" to="/explore">
            Review the Lineup
          </Link>
        }
      />
    </div>
  )
}

export default ComparePage
