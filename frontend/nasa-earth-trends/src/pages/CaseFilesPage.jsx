import { Link } from 'react-router-dom'

import Panel from '../components/Panel.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'

const cases = [
  ['01', 'A guided investigation will be added when the analysis examples are available.'],
  ['02', 'Each case will include its period, product, coverage and method.'],
  ['03', 'Results will distinguish observation estimates from model reanalysis.'],
]

function CaseFilesPage() {
  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>Case Files</h1>
          <p>
            Three worked investigations, built to show how to read an
            Earth-system trend without jumping to conclusions.
          </p>
        </div>
        <Link className="button button-secondary" to="/explore">
          Explore the catalogue
        </Link>
      </div>

      <SampleDataWarning />

      <Panel title="Investigations" flush>
        <ol className="case-list">
          {cases.map(([number, text]) => (
            <li className="case-row" key={number}>
              <span className="case-number">{number}</span>
              <div>
                <strong>Coming soon</strong>
                <p>{text}</p>
              </div>
              <span className="status-pill status-coming_soon">Pending</span>
            </li>
          ))}
        </ol>
      </Panel>
    </div>
  )
}

export default CaseFilesPage
