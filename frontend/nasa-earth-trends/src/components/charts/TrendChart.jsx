import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const chartFrame = [{ year: '—', value: null }]

function TrendChart({ data = chartFrame }) {
  return (
    <div className="trend-chart">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart
          data={data}
          margin={{ top: 12, right: 16, bottom: 4, left: 0 }}
        >
          <CartesianGrid
            stroke="#d3d8df"
            strokeDasharray="2 5"
            vertical={false}
          />
          <XAxis
            dataKey="year"
            tick={{ fill: '#5b6573', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide domain={['auto', 'auto']} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#0b3d91"
            strokeWidth={3}
            dot={false}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="chart-placeholder">
        Supplied historical series will appear here
      </div>
    </div>
  )
}

export default TrendChart
