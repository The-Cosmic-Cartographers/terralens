import { useMemo, useState } from 'react'

import DropdownMenu from '../components/DropdownMenu.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import ProductBadge from '../components/ProductBadge.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import VerdictBadge from '../components/VerdictBadge.jsx'
import { regions } from '../data/regionOptions.js'
import { useData } from '../hooks/useData.js'
import { formatIntervalPerDecade, formatP, formatSigned } from '../utils/format.js'

// The paired regions of the Opposite Trends view (doc 11 and NAS-34); every region is an app region.
const pairs = [
  ['ireland', 'iberia'],
  ['sahel', 'iberia'],
  ['us_southwest', 'ireland'],
  ['sahel', 'nw_south_asia'],
]

const labels = {
  dublin_no2: 'Dublin',
  delhi_no2: 'Delhi',
}

function regionName(regionId) {
  return labels[regionId] || regions.find((region) => region.id === regionId)?.name || regionId
}

function directionSymbol(direction) {
  if (direction === 'increasing') return '↑'
  if (direction === 'decreasing') return '↓'
  return '→'
}

function slopePerDecade(value) {
  return formatSigned(value == null ? null : Number(value) * 10)
}

function CompareCard({ result }) {
  return (
    <article className="compare-result-card">
      <div className="compare-result-heading">
        <div>
          <span className="section-index">{result.region_id}</span>
          <h3>{regionName(result.region_id)}</h3>
        </div>
        <span className="compare-direction" aria-label={result.trend_direction || 'direction not supplied'}>
          {directionSymbol(result.trend_direction)}
        </span>
      </div>
      <VerdictBadge verdict={result.verdict} />
      <dl className="kv">
        <div><dt>Rate</dt><dd>{slopePerDecade(result.sen_slope_per_year)} {result.unit_per_year?.replace('/yr', '/decade') || 'per decade'}</dd></div>
        <div><dt>95% interval</dt><dd>{formatIntervalPerDecade(result.confidence_interval_95)}</dd></div>
        <div><dt>Adjusted p</dt><dd>{formatP(result.adjusted_p_value)}</dd></div>
        <div><dt>Period</dt><dd>{result.period_start} – {result.period_end}</dd></div>
      </dl>
      <ProductBadge type={result.product_type} />
    </article>
  )
}

function ComparePage() {
  const [datasetId, setDatasetId] = useState('merra2_m2tmnxslv')
  const [pairIndex, setPairIndex] = useState(2)
  const { data: catalogue, loading: catalogueLoading } = useData('catalogue')
  const { data, loading, error } = useData('compare', { datasetId })
  const [leftId, rightId] = pairs[pairIndex]
  const selectedResults = useMemo(() => {
    const results = data?.results || []
    return [leftId, rightId].map((id) => results.find((result) => result.region_id === id)).filter(Boolean)
  }, [data, leftId, rightId])
  const selectedDataset = catalogue?.find((item) => item.dataset_id === datasetId)

  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>Opposite Trends</h1>
          <p>One variable. Two places. The same evidence frame.</p>
        </div>
        <ProductBadge type={selectedDataset?.product_type || 'reanalysis'} />
      </div>

      <SampleDataWarning />

      <div className="grid">
        <Panel className="span-12" title="Choose the comparison">
          <div className="compare-controls">
            <div className="field">
              <span>Variable / dataset</span>
              <DropdownMenu
                label="Variable / dataset"
                value={datasetId}
                disabled={catalogueLoading}
                options={(catalogue || [{ dataset_id: 'merra2_m2tmnxslv', label: 'Air temperature (2 m)' }]).map((item) => ({
                  value: item.dataset_id,
                  label: item.label || item.dataset_id,
                }))}
                onChange={setDatasetId}
              />
            </div>
            <div className="field">
              <span>Paired regions</span>
              <DropdownMenu
                label="Paired regions"
                value={pairIndex}
                options={pairs.map(([first, second], index) => ({
                  value: index,
                  label: `${regionName(first)} ↔ ${regionName(second)}`,
                }))}
                onChange={(nextIndex) => setPairIndex(Number(nextIndex))}
              />
            </div>
          </div>
          {data?.period_note && <p className="period-note">{data.period_note}</p>}
        </Panel>

        <Panel className="span-12" title={`${regionName(leftId)} ↔ ${regionName(rightId)}`} flush>
          {loading && <LoadingState label="Loading comparison results" />}
          {error && <ErrorState message={error.message} />}
          {!loading && !error && selectedResults.length === 2 ? (
            <div className="compare-results">
              {selectedResults.map((result) => <CompareCard key={result.region_id} result={result} />)}
            </div>
          ) : (!loading && !error && (
            <EmptyState
              title="This pairing has no supplied result yet"
              message="The compare frame is ready, but this variable and pair must be supplied by the analysis export before it can be shown."
            />
          ))}
        </Panel>

        <Panel className="span-12" title="How to read the arrows">
          <p>The arrow is the direction supplied by analysis for each place. It is not a causal explanation, and a difference between places is not itself a claim about why either record changed.</p>
        </Panel>
      </div>
    </div>
  )
}

export default ComparePage
