import { Link, useParams } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import TrendChart from '../components/charts/TrendChart.jsx'

function VariableDetailPage() {
  const { variableId } = useParams()
  const displayName = variableId?.replaceAll('_', ' ')

  return (
    <div className="content-page">
      <Link className="back-link" to="/explore">
        ← Back to the Lineup
      </Link>

      <div className="page-heading detail-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-line" />
            Trend detail
          </div>
          <h1>{displayName}</h1>
          <p>Historical evidence and methodology for this variable.</p>
        </div>
        <ProductBadge type="reanalysis" />
      </div>

      <SampleDataWarning />

      <section className="detail-grid">
        <div className="chart-card">
          <div className="section-label">
            Historical series <span>Chart foundation</span>
          </div>
          <TrendChart />
        </div>

        <aside className="method-card">
          <span className="card-kicker">Evidence record</span>
          <h2>Results are precomputed.</h2>
          <p>
            This view will display supplied trend statistics, coverage and
            provenance once the result endpoint is available.
          </p>
          <div className="metadata-list">
            <div>
              <span>Variable</span>
              <strong>{variableId}</strong>
            </div>
            <div>
              <span>Trend method</span>
              <strong>Supplied by analysis</strong>
            </div>
            <div>
              <span>Product type</span>
              <strong>Model reanalysis</strong>
            </div>
          </div>
        </aside>
      </section>

      <EmptyState
        title="Trend result not connected yet"
        message="The current backend contract does not expose a variable-result endpoint. No scientific result is being invented here."
      />
    </div>
  )
}

export default VariableDetailPage
