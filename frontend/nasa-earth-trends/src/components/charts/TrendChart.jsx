import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatChartValue } from '../../utils/format.js'

function median(values) {
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
}

function TrendChart({ data = [], trend = null, dataKey = 'value' }) {
  // The supplied Sen slope is per year and the points are monthly. Draw the line
  // slope * years + intercept, with the intercept the median of (value - slope * years),
  // which is the Sen line's own definition; nothing is re-tested here.
  const slope = trend?.sen_slope_per_year == null ? null : Number(trend.sen_slope_per_year)
  const valid = data
    .map((point, index) => ({ index, value: point[dataKey] }))
    .filter((point) => point.value != null && Number.isFinite(Number(point.value)))
  const intercept = slope == null || !valid.length
    ? null
    : median(valid.map((point) => Number(point.value) - slope * (point.index / 12)))
  const chartData = data.map((point, index) => ({
    ...point,
    index,
    trendLine: intercept == null || point[dataKey] == null
      ? null
      : intercept + slope * (index / 12),
  }))

  // Ticks sit on whole years (multiples of 5 for a long record) so the axis never
  // rounds the last December up to the following year.
  const times = chartData.map((point) => point.t).filter((value) => Number.isFinite(value))
  const first = Math.min(...times)
  const last = Math.max(...times)
  const step = last - first > 25 ? 5 : 2
  const ticks = []
  for (let year = Math.ceil(first / step) * step; year <= last; year += step) ticks.push(year)

  if (!chartData.length) {
    return (
      <div className="trend-chart chart-empty">
        No measured series was supplied for this selection.
      </div>
    )
  }

  return (
    <div className="trend-chart">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="2 5" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            domain={['dataMin', 'dataMax']}
            ticks={ticks}
            tickFormatter={(value) => String(Math.round(value))}
            allowDecimals={false}
            tick={{ fill: 'var(--chart-axis)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: 'var(--chart-axis)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={42}
          />
          <Tooltip
            formatter={(value, name) => [formatChartValue(value), name]}
            labelFormatter={(value) => {
              const year = Math.floor(value + 1e-6)
              const month = Math.round((value - year) * 12) + 1
              return `${year}-${String(month).padStart(2, '0')}`
            }}
            contentStyle={{
              background: 'var(--surface-strong)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              color: 'var(--text)',
            }}
          />
          <Area dataKey="ciHigh" stroke="none" fill="var(--chart-band)" fillOpacity={0.35} isAnimationActive={false} />
          <Area dataKey="ciLow" stroke="none" fill="var(--surface)" fillOpacity={1} isAnimationActive={false} />
          <Line
            type="monotone"
            dataKey={dataKey}
            name="Measured"
            stroke="var(--chart-line)"
            strokeWidth={2.5}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          {trend?.sen_slope_per_year != null && (
            <Line
              type="monotone"
              dataKey="trendLine"
              name="Supplied trend line"
              stroke="var(--chart-trend)"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default TrendChart
