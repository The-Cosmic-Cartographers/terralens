import { Link } from 'react-router-dom'

import DatasetTable from '../components/DatasetTable.jsx'
import GlossaryPanel from '../components/GlossaryPanel.jsx'
import InvestigationStart from '../components/InvestigationStart.jsx'
import KpiTile from '../components/KpiTile.jsx'
import Panel from '../components/Panel.jsx'
import RegionExplorer from '../components/RegionExplorer.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import { regions as regionOptions } from '../data/regionOptions.js'
import { useData } from '../hooks/useData.js'

function HomePage() {
  const { data: catalogue } = useData('catalogue')
  const { data: regions } = useData('regions')
  const { data: health } = useData('health')

  const items = catalogue ?? []
  const ready = items.filter((item) => item.status === 'ready').length
  // regions.json also carries the Dublin and Delhi boxes that exist only for the
  // NO2 comparison. Counting it whole reported seven study regions; the study
  // set is the five in the region options that the snapshot actually covers.
  const studyRegions = regionOptions.filter((option) =>
    regions?.some((item) => item.region_id === option.id),
  )

  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>Overview</h1>
          <p>
            A careful way to investigate long-term environmental change. Pick a
            place, inspect the signals, and follow the evidence back to its
            source.
          </p>
        </div>
        <Link className="button button-primary" to="/explore">
          Open the Lineup
        </Link>
      </div>

      <SampleDataWarning />

      <InvestigationStart />

      <div className="kpi-row">
        <KpiTile
          label="Datasets ready"
          value={catalogue ? `${ready} of ${items.length}` : '—'}
          note="Listed in the catalogue"
          tone="blue"
        />
        <KpiTile
          label="Study regions"
          value={regions ? studyRegions.length : '—'}
          note={studyRegions.map((region) => region.name).join(', ')}
        />
        <KpiTile
          label="Analysis window"
          value="1980–2025"
          note="Monthly, precomputed"
        />
        <KpiTile
          label="Data version"
          value={health?.data_version ?? '—'}
          note="Snapshot on screen"
          tone="compact"
        />
      </div>

      <div className="grid">
        <RegionExplorer />

        <Panel
          className="span-8"
          title="Variable catalogue"
          meta={<Link to="/explore">Open full Lineup →</Link>}
          flush
        >
          <DatasetTable items={items} />
        </Panel>

        <div className="span-4 stack">
          <Panel title="How to read a result">
            <p>
              Every result names its product type, analysis period, data
              coverage, method, limitations and provenance. It describes what
              the data shows over the measured period. It does not forecast or
              claim causes.
            </p>
            <p className="method-note">
              <strong>Minimum data.</strong> Ten complete years (all twelve
              months present) and no more than 20% of months missing; months
              under half-covered are dropped first. Below that, no test is run —
              the record is marked “Not enough data”.
            </p>
            <Link className="text-link" to="/case-files">
              How to read a case file →
            </Link>
          </Panel>

          <Panel title="Comparison track" className="panel-accent">
            <p>
              One atmosphere, two stories: nitrogen dioxide over Delhi and
              Dublin, once the comparison result is available.
            </p>
            <Link className="button button-secondary" to="/compare">
              Open Opposite Trends
            </Link>
          </Panel>
        </div>

        <div className="span-12">
          <GlossaryPanel />
        </div>
      </div>
    </div>
  )
}

export default HomePage
