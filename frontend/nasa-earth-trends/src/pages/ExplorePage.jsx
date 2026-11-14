import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import { useData } from '../hooks/useData.js'

function ExplorePage() {
  const { data, loading, error, mode } = useData('catalogue')

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-line" />
            Explore
          </div>
          <h1>The Lineup</h1>
          <p>Which environmental signals are moving most clearly?</p>
        </div>
        <span className="period-chip">
          {mode === 'static' ? 'Static snapshot' : 'Live API'}
        </span>
      </div>

      <SampleDataWarning />

      {loading && <LoadingState label="Loading available variables" />}

      {error && <ErrorState message={error.message} />}

      {!loading && !error && (!data || data.length === 0) && (
        <EmptyState
          title="No variables available"
          message="The catalogue is empty for this data source."
        />
      )}

      {!loading && !error && data?.length > 0 && (
        <div className="variable-list">
          {data.map((item, index) => (
            <Link
              className="variable-row"
              to={`/explore/${item.variable_id}`}
              key={item.dataset_id}
            >
              <span className="rank">0{index + 1}</span>
              <span className="variable-name">
                <strong>{item.label}</strong>
                <small>
                  {item.variable_id} · {item.period_start} — {item.period_end}
                </small>
              </span>
              <span className="variable-unit">{item.unit}</span>
              <ProductBadge type="reanalysis" />
              <span className={`catalogue-status ${item.status}`}>
                {item.status === 'ready' ? 'Available' : 'Coming soon'}
              </span>
              <span className="row-arrow">→</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default ExplorePage
