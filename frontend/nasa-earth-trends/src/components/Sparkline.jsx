const WIDTH = 150
const HEIGHT = 42
const PAD = 3

function Sparkline({ values = [] }) {
  if (!values.length) return <span className="sparkline-empty">No series</span>

  const numbers = values.map(Number).filter(Number.isFinite)
  if (!numbers.length) return <span className="sparkline-empty">No series</span>

  const min = Math.min(...numbers)
  const max = Math.max(...numbers)
  const range = max - min || 1
  const step = numbers.length > 1 ? (WIDTH - PAD * 2) / (numbers.length - 1) : 0
  const points = numbers
    .map((value, index) => {
      const x = PAD + index * step
      const y = HEIGHT - PAD - ((value - min) / range) * (HEIGHT - PAD * 2)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <div className="sparkline" aria-label="Supplied trend sparkline">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  )
}

export default Sparkline
