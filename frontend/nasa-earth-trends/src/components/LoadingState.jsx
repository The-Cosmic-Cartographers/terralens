// A small trend line draws itself beside the label: the product's own shape,
// and the label still says exactly what is loading.
const TRACE = '2,18 9,14 15,16 21,9 27,12 33,6 39,8 46,3'

function LoadingState({ label = 'Loading' }) {
  return (
    <div className="state-card state-loading" role="status">
      <svg className="trace-loader" viewBox="0 0 48 22" aria-hidden="true">
        <polyline className="trace-loader-track" points={TRACE} />
        <polyline className="trace-loader-line" points={TRACE} pathLength="100" />
      </svg>
      <span>{label}…</span>
    </div>
  )
}

export default LoadingState
