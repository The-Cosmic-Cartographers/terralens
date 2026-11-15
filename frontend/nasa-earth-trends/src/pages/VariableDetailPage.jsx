import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import TimeMachine from '../components/TimeMachine.jsx'
import TrendChart from '../components/charts/TrendChart.jsx'
import { regions } from '../data/regionOptions.js'
import { useData } from '../hooks/useData.js'
import { formatP, formatSlope, methodLabel, verdictLabel } from '../utils/format.js'

const fallbackDataset = {
  t2m: {
    dataset_id: 'merra2_m2tmnxslv',
    variable_id: 't2m',
    label: 'Air temperature (2 m)',
    unit: '°C',
    product_type: 'reanalysis',
  },
}

function VariableDetailPage() {
  const { variableId } = useParams()
  const [searchParams] = useSearchParams()
  const [seriesMode, setSeriesMode] = useState('value')
  const regionId = searchParams.get('region') || regions[0].id
  const { data: catalogue, loading: catalogueLoading } = useData('catalogue')
  const { data: trend, loading: trendLoading, error: trendError } = useData('trend', {
    regionId,
    datasetId: searchParams.get('dataset') || fallbackDataset[variableId]?.dataset_id,
  })
  const dataset = catalogue?.find((item) => item.variable_id === variableId)
    || fallbackDataset[variableId]
  const datasetId = searchParams.get('dataset') || dataset?.dataset_id
  const { data: series } = useData('series', { regionId, datasetId })
  const { data: metadata } = useData('metadata', { datasetId })
  const chartData = useMemo(() => (series?.rows || []).map((row) => ({
    label: row.timestamp?.slice(0, 4),
    t: Number(row.timestamp?.slice(0, 4)) + (Number(row.timestamp?.slice(5, 7)) - 1) / 12,
    value: seriesMode === 'anomaly' ? row.anomaly : row.value,
    ciLow: null,
    ciHigh: null,
  })), [series, seriesMode])
  const region = regions.find((item) => item.id === regionId) || regions[0]
  const loading = catalogueLoading || trendLoading

  if (loading) return <div className="page"><LoadingState label="Loading supplied variable evidence" /></div>

  return (
    <div className="page">
      <Link className="back-link" to="/explore">← Back to the Lineup</Link>

      <div className="page-title">
        <div>
          <h1 className="keep-case">{dataset?.label || variableId?.replaceAll('_', ' ')}</h1>
          <p>{region.name} · {trend?.period_start || dataset?.period_start || 'Period pending'} to {trend?.period_end || dataset?.period_end || 'period pending'}</p>
        </div>
        <ProductBadge type={trend?.product_type || dataset?.product_type || 'reanalysis'} />
      </div>

      <SampleDataWarning />
      {trendError && <ErrorState message={trendError.message} />}

      <div className="grid">
        <Panel className="span-8" title="Historical series" meta={<span className="chip">Chart foundation</span>}>
          <div className="chart-toolbar" role="group" aria-label="Series display mode">
            <button type="button" className={seriesMode === 'value' ? 'active' : ''} onClick={() => setSeriesMode('value')}>Measured</button>
            <button type="button" className={seriesMode === 'anomaly' ? 'active' : ''} onClick={() => setSeriesMode('anomaly')}>Anomaly</button>
          </div>
          {chartData.length ? <TrendChart data={chartData} trend={trend} /> : <EmptyState title="Historical series unavailable" message="No monthly series was supplied for this region and variable." />}
        </Panel>

        <Panel className="span-4" title="Evidence record">
          <dl className="kv">
            <div><dt>Variable</dt><dd>{dataset?.label || variableId}</dd></div>
            <div><dt>Unit</dt><dd>{trend?.unit_per_year?.replace('/yr', '') || series?.unit || dataset?.unit || 'Pending'}</dd></div>
            <div><dt>Trend method</dt><dd>{methodLabel(trend?.method)}</dd></div>
            <div><dt>Coverage</dt><dd>{trend?.mean_coverage_fraction == null ? 'Pending' : `${(trend.mean_coverage_fraction * 100).toFixed(1)}%`}</dd></div>
            <div><dt>Source</dt><dd>{metadata?.provenance?.product || 'Product metadata pending'}</dd></div>
          </dl>
        </Panel>

        <Panel className="span-12" title="Trend result" flush>
          {trend ? (
            <div className="evidence-grid">
              <div><span>Verdict</span><strong>{verdictLabel(trend.verdict)}</strong></div>
              <div><span>Sen slope / year</span><strong>{formatSlope(trend.sen_slope_per_year)}</strong></div>
              <div><span>95% confidence interval</span><strong>{trend.confidence_interval_95?.map((value) => formatSlope(value, trend.sen_slope_per_year)).join(' to ') || '—'}</strong></div>
              <div><span>Adjusted p-value</span><strong>{formatP(trend.adjusted_p_value)}</strong></div>
              <div><span>Observations</span><strong>{trend.observation_count ?? '—'}</strong></div>
            </div>
          ) : (
            <EmptyState title="No trend result supplied" message="No scientific result is being invented here; connect the matching precomputed result to populate this record." />
          )}
        </Panel>

        <Panel className="span-12" title="Time Machine">
          <TimeMachine regionId={regionId} datasetId={datasetId} headline={trend} />
        </Panel>
      </div>
    </div>
  )
}

export default VariableDetailPage
