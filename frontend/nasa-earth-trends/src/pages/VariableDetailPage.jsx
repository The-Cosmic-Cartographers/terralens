import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import SourceLink from '../components/SourceLink.jsx'
import TimeMachine from '../components/TimeMachine.jsx'
import TrendChart from '../components/charts/TrendChart.jsx'
import { regions } from '../data/regionOptions.js'
import { accessRecord, provenanceUrl } from '../data/sources.js'
import { useData } from '../hooks/useData.js'
import { useWindow } from '../state/window.js'
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
  const { startYear, endYear } = useWindow()
  const chartData = useMemo(() => (series?.rows || []).map((row) => ({
    label: row.timestamp?.slice(0, 4),
    t: Number(row.timestamp?.slice(0, 4)) + (Number(row.timestamp?.slice(5, 7)) - 1) / 12,
    value: row.value,
    ciLow: null,
    ciHigh: null,
  })), [series])
  // The header picker trims the plotted years. It never recalculates anything:
  // the supplied trend statistics keep describing the whole record, and the
  // note under the chart says so whenever the plot is shorter than the record.
  const plottedData = useMemo(
    () => chartData.filter((point) => {
      const year = Number(point.label)
      return Number.isFinite(year) && year >= startYear && year <= endYear
    }),
    [chartData, startYear, endYear],
  )
  const access = accessRecord(metadata?.provenance, regionId)
  const isTrimmed = plottedData.length > 0 && plottedData.length < chartData.length
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
        <Panel className="span-8" title="Historical series">
          {chartData.length ? <TrendChart data={plottedData} trend={trend} /> : <EmptyState title="Historical series unavailable" message="No monthly series was supplied for this region and variable." />}
          {isTrimmed && (
            <p className="chart-note">
              Plot stops at {endYear}. The trend statistics on this page still describe the full supplied
              record{trend?.period_start && trend?.period_end ? ` (${trend.period_start.slice(0, 4)}–${trend.period_end.slice(0, 4)})` : ''}.
            </p>
          )}
        </Panel>

        <Panel className="span-4" title="Evidence record">
          <dl className="kv">
            <div><dt>Variable</dt><dd>{dataset?.label || variableId}</dd></div>
            <div><dt>Unit</dt><dd>{trend?.unit_per_year?.replace('/yr', '') || series?.unit || dataset?.unit || 'Pending'}</dd></div>
            <div><dt>Trend method</dt><dd>{methodLabel(trend?.method)}</dd></div>
            <div><dt>Coverage</dt><dd>{trend?.mean_coverage_fraction == null ? 'Pending' : `${(trend.mean_coverage_fraction * 100).toFixed(1)}%`}</dd></div>
            <div>
              <dt>Source</dt>
              <dd>
                <SourceLink href={provenanceUrl(metadata?.provenance, regionId)}>
                  {metadata?.provenance?.product || 'Product metadata pending'}
                </SourceLink>
              </dd>
            </div>
            {access && (
              <div>
                <dt>Access</dt>
                <dd>{access.href ? <SourceLink href={access.href}>{access.label}</SourceLink> : access.label}</dd>
              </div>
            )}
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
