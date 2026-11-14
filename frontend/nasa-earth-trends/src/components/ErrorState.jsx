function ErrorState({
  message = 'Something went wrong while loading this data.',
}) {
  return (
    <div className="state-card state-error" role="alert">
      <strong>Data unavailable</strong>
      <span>{message}</span>
    </div>
  )
}

export default ErrorState
