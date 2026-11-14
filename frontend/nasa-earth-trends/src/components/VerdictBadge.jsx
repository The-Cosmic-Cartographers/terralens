const verdictLabels = {
  significant: 'Significant',
  weak_evidence: 'Weak evidence',
  no_clear_trend: 'No clear trend',
  not_enough_data: 'Not enough data',
}

function VerdictBadge({ verdict = 'not_enough_data' }) {
  return (
    <span className={`verdict-badge ${verdict}`}>
      {verdictLabels[verdict] || verdict}
    </span>
  )
}

export default VerdictBadge
