function SourceLink({ href, children, className = '' }) {
  if (!href) return <span className={className}>{children}</span>

  return (
    <a
      className={`source-link ${className}`.trim()}
      href={href}
      target="_blank"
      rel="noreferrer noopener"
    >
      {children}
      <span className="source-link-arrow" aria-hidden="true">↗</span>
    </a>
  )
}

export default SourceLink
