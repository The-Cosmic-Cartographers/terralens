import { Line, LineChart, ResponsiveContainer } from 'recharts'

function Sparkline({ values = [] }) {
  const data = values.map((value, index) => ({ index, value }))

  if (!data.length) return <span className="sparkline-empty">No series</span>

  return (
    <div className="sparkline" aria-label="Supplied trend sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            dataKey="value"
            type="monotone"
            stroke="currentColor"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default Sparkline
