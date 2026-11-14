import Panel from './Panel.jsx'
import { variableGlossary, verdictGlossary } from '../data/glossary.js'

function GlossaryPanel() {
  return (
    <Panel title="Plain-language glossary">
      <div className="glossary-list">
        {variableGlossary.map((item) => (
          <article className="glossary-item" key={item.variableId}>
            <div className="glossary-heading">
              <strong>{item.name}</strong>
              <span className="chip">{item.unit}</span>
            </div>
            <p>{item.definition}</p>
            <small>{item.whyItMatters}</small>
            <span className="glossary-source">{item.source}</span>
          </article>
        ))}
      </div>
      <div className="verdict-glossary">
        <strong>Verdicts</strong>
        {verdictGlossary.map(([key, label, explanation]) => (
          <div key={key}>
            <span className={`verdict-badge ${key}`}>{label}</span>
            <span>{explanation}</span>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export default GlossaryPanel
