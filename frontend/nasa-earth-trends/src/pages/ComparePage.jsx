import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'

function ComparePage() {
  return (
    <div className="content-page">
      <div className="eyebrow">
        <span className="eyebrow-line" />
        Compare
      </div>
      <h1>Opposite Trends</h1>
      <p className="intro-copy">
        Put the same variable in two different places. Context changes what a
        signal means.
      </p>

      <SampleDataWarning />

      <EmptyState
        title="Comparison data is waiting on the API contract"
        message="The backend model defines CompareResult, but its route is not implemented yet. This screen is ready for that response without fabricating findings."
        action={
          <Link className="button button-secondary" to="/explore">
            Browse available variables
          </Link>
        }
      />
    </div>
  )
}

export default ComparePage
