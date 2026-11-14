import { Link } from 'react-router-dom'

import SampleDataWarning from '../components/SampleDataWarning.jsx'

function CaseFilesPage() {
  return (
    <div className="content-page">
      <div className="eyebrow">
        <span className="eyebrow-line" />
        Field notes
      </div>
      <h1>Case Files</h1>
      <p className="intro-copy">
        Three worked investigations, built to show how to read an Earth-system
        trend without jumping to conclusions.
      </p>

      <SampleDataWarning />

      <div className="case-list">
        <div className="case-row">
          <span>01</span>
          <div>
            <strong>Coming soon</strong>
            <p>
              A guided investigation will be added when the analysis examples
              are available.
            </p>
          </div>
          <span>→</span>
        </div>

        <div className="case-row">
          <span>02</span>
          <div>
            <strong>Coming soon</strong>
            <p>Each case will include its period, product, coverage and method.</p>
          </div>
          <span>→</span>
        </div>

        <div className="case-row">
          <span>03</span>
          <div>
            <strong>Coming soon</strong>
            <p>
              Results will distinguish observation estimates from model
              reanalysis.
            </p>
          </div>
          <span>→</span>
        </div>
      </div>

      <Link className="text-link" to="/explore">
        Explore the available catalogue →
      </Link>
    </div>
  )
}

export default CaseFilesPage
