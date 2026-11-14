import { useData } from '../hooks/useData.js'

// Shown only when the data on screen is marked SAMPLE (see health.data_version).
function SampleDataWarning() {
  const { data } = useData('health')

  if (!data?.data_version?.toUpperCase().includes('SAMPLE')) {
    return null
  }

  return (
    <div className="sample-warning">
      <span className="warning-icon">!</span>
      <span>
        <strong>SAMPLE DATA — NOT NASA DATA.</strong> Fixture values are for
        interface development only.
      </span>
    </div>
  )
}

export default SampleDataWarning
