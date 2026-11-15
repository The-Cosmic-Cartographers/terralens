import Panel from './Panel.jsx'
import SourceLink from './SourceLink.jsx'
import { variableGlossary, verdictGlossary } from '../data/glossary.js'
import { datasetSourceUrl } from '../data/sources.js'

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
            <SourceLink className="glossary-source" href={datasetSourceUrl(item.datasetId)}>
              {item.source}
            </SourceLink>
          </article>
        ))}
      </div>
      <div className="verdict-glossary">
        <strong>Verdicts</strong>
        <p className="verdict-glossary-note">
          A p-value asks how surprising the data would be if nothing were changing. It is not the
          probability that a trend is real, and it says nothing about how large the change is. These
          values are adjusted across the results being compared (Benjamini–Hochberg), so 0.05 holds for
          the set as a whole, not for one test on its own.
        </p>
        {verdictGlossary.map((verdict) => (
          <div className="verdict-item" key={verdict.key}>
            <span className={`verdict-badge ${verdict.key}`}>{verdict.label}</span>
            <span className="verdict-copy">
              <strong>{verdict.rule}</strong>
              <small>{verdict.explanation}</small>
            </span>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export default GlossaryPanel
