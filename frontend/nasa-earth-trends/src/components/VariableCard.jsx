import SourceLink from './SourceLink.jsx'
import { datasetSourceUrl } from '../data/sources.js'

function VariableCard({ variable, index }) {
  return (
    <article className="variable-card">
      <div className="variable-card-topline">
        <span className="variable-number">0{index + 1}</span>
        <span className="variable-unit">{variable.unit}</span>
      </div>
      <div className="variable-glyph" aria-hidden="true">
        {variable.glyph}
      </div>
      <h3>{variable.name}</h3>
      <p>{variable.description}</p>
      <details>
        <summary>Why it matters</summary>
        <p>{variable.significance}</p>
      </details>
      <div className="variable-card-footer">
        <SourceLink href={datasetSourceUrl(variable.datasetId)}>{variable.source}</SourceLink>
        <span className="awaiting-result">Result supplied by analysis</span>
      </div>
    </article>
  )
}

export default VariableCard
