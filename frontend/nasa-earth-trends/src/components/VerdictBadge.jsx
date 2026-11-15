import { verdictLabel } from '../utils/format.js'

function VerdictBadge({ verdict = 'not_enough_data' }) {
  return (
    <span className={`verdict-badge ${verdict}`}>
      {verdictLabel(verdict)}
    </span>
  )
}

export default VerdictBadge
