function Panel({ title, meta, children, className = '', flush = false }) {
  return (
    <section className={`panel ${className}`.trim()}>
      <header className="panel-head">
        <h2 className="panel-title">{title}</h2>
        {meta && <div className="panel-meta">{meta}</div>}
      </header>
      <div className={flush ? 'panel-body panel-body-flush' : 'panel-body'}>
        {children}
      </div>
    </section>
  )
}

export default Panel
