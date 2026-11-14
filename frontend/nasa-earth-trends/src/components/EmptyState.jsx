function EmptyState({ title, message, action }) {
  return (
    <div className="state-card state-empty">
      <span className="empty-mark">—</span>
      <div>
        <strong>{title}</strong>
        <span>{message}</span>
        {action && <div className="state-action">{action}</div>}
      </div>
    </div>
  )
}

export default EmptyState
