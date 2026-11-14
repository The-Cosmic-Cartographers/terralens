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

function TrendChart({ data = [], trend = null, dataKey = 'value' }) {
  const chartData = data.map((point, index) => ({
    ...point,
    index,
    trendLine: trend?.sen_slope_per_year == null || point[dataKey] == null
      ? null
      : Number(point[dataKey]) + (Number(trend.sen_slope_per_year) * index),
  }))

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
            dataKey="label"
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
            contentStyle={{
              background: 'var(--surface-strong)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              color: 'var(--text)',
            }}
          />
          <Area dataKey="ciHigh" stroke="none" fill="var(--chart-band)" fillOpacity={0.35} />
          <Area dataKey="ciLow" stroke="none" fill="var(--surface)" fillOpacity={1} />
          <Line
            type="monotone"
            dataKey={dataKey}
            name="Measured"
            stroke="var(--chart-line)"
            strokeWidth={2.5}
            dot={false}
            connectNulls={false}
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
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default TrendChart
