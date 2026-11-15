// Placeholder rows in the exact grid of LineupRow, so the real rows land in
// place without the panel jumping. Each region supplies five ranked signals.
function LineupSkeleton({ rows = 5, label = 'Loading the ranked Lineup' }) {
  return (
    <div className="lineup-result-list" role="status">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }, (_, index) => (
        <div className="lineup-result-row lineup-skeleton-row" key={index} aria-hidden="true">
          <span className="skeleton sk-rank" />
          <span className="lineup-result-name">
            <span className="skeleton sk-title" />
            <span className="skeleton sk-sub" />
          </span>
          <span className="skeleton sk-spark" />
          <span className="lineup-slope">
            <span className="skeleton sk-num" />
          </span>
          <span className="lineup-verdict">
            <span className="skeleton sk-badge" />
          </span>
          <span className="skeleton sk-product" />
          <span className="skeleton sk-chevron" />
        </div>
      ))}
    </div>
  )
}

export default LineupSkeleton
