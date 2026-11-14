import { Link, useParams } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import TrendChart from '../components/charts/TrendChart.jsx'

function VariableDetailPage() {
  const { variableId } = useParams()
  const displayName = variableId?.replaceAll('_', ' ')

  return (
    <div className="page">
      <Link className="back-link" to="/explore">
        ← Back to the Lineup
      </Link>

      <div className="page-title">
        <div>
          <h1>{displayName}</h1>
          <p>Historical evidence and methodology for this variable.</p>
        </div>
        <ProductBadge type="reanalysis" />
      </div>

      <SampleDataWarning />

      <div className="grid">
        <Panel
          className="span-8"
          title="Historical series"
          meta={<span className="chip">Chart foundation</span>}
        >
          <TrendChart />
        </Panel>

        <Panel className="span-4" title="Evidence record">
          <p>
            Results are precomputed. This view will display supplied trend
            statistics, coverage and provenance once the result endpoint is
            available.
          </p>
          <dl className="kv">
            <div>
              <dt>Variable</dt>
              <dd className="num">{variableId}</dd>
            </div>
            <div>
              <dt>Trend method</dt>
              <dd>Supplied by analysis</dd>
            </div>
            <div>
              <dt>Product type</dt>
              <dd>Model reanalysis</dd>
            </div>
          </dl>
        </Panel>

        <Panel className="span-12" title="Trend result" flush>
          <EmptyState
            title="Trend result not connected yet"
            message="The current backend contract does not expose a variable-result endpoint. No scientific result is being invented here."
          />
        </Panel>
      </div>
    </div>
  )
}

export default VariableDetailPage
