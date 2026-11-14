import { Link } from 'react-router-dom'

import ProductBadge from './ProductBadge.jsx'
import Sparkline from './Sparkline.jsx'
import VerdictBadge from './VerdictBadge.jsx'

function LineupRow({ row, rank }) {
  const trend = row.trend || {}
  const slope = trend.sen_slope_per_year == null
    ? null
    : Number(trend.sen_slope_per_year) * 10

  return (
    <Link
      className="lineup-result-row"
      to={`/explore/${row.variable_id}?region=${trend.region_id || row.region_id}&dataset=${row.dataset_id}`}
    >
      <span className="lineup-rank">{String(rank).padStart(2, '0')}</span>
      <span className="lineup-result-name">
        <strong>{row.label}</strong>
        <small>{row.definition || 'Definition supplied with the result.'}</small>
      </span>
      <Sparkline values={row.sparkline} />
      <span className="lineup-slope">
        {slope == null ? '—' : slope.toFixed(3)}
        <small>{trend.unit_per_year?.replace('/yr', '/decade') || 'per decade'}</small>
      </span>
      <span className="lineup-verdict">
        <VerdictBadge verdict={trend.verdict} />
        <small>
          {trend.period_start || row.period_start} — {trend.period_end || row.period_end}
        </small>
      </span>
      <ProductBadge type={row.product_type || trend.product_type} />
    </Link>
  )
}

export default LineupRow
