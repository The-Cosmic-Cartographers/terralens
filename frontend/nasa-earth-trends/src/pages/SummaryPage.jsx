import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import VerdictBadge from '../components/VerdictBadge.jsx'
import { regions } from '../data/regionOptions.js'
import { useData } from '../hooks/useData.js'
import { useWindowedLineups } from '../hooks/useWindowedLineups.js'
import { formatSlope, verdictLabel } from '../utils/format.js'

const variables = [
  { id: 't2m', fallbackLabel: 'Air temperature' },
  { id: 'soil_moisture_0_5', fallbackLabel: 'Soil moisture' },
  { id: 'evapotranspiration', fallbackLabel: 'Evapotranspiration' },
  { id: 'precipitation', fallbackLabel: 'Precipitation' },
  { id: 'aerosol', fallbackLabel: 'Aerosol optical depth' },
]

function shortName(name) {
  return name.split(' (')[0]
}

function listNames(names) {
  if (names.length <= 1) return names[0] ?? ''
  return `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`
}

function trendFor(lineup, variableId) {
  const row = lineup?.rows?.find((item) => item.variable_id === variableId)
  return row?.window_unavailable ? undefined : row?.trend
}

function unitPerDecade(trend) {
  const unit = trend?.unit_per_year
  if (!unit) return ''
  if (unit === '1/yr') return 'per decade'
  return unit.replace(' (annual total)/yr', ' (annual total)/decade').replace('/yr', '/decade')
}

function slopePerDecade(trend) {
  if (trend?.sen_slope_per_year == null) return '—'
  return `${formatSlope(Number(trend.sen_slope_per_year) * 10)} ${unitPerDecade(trend)}`.trim()
}

function directionVerb(trend) {
  if (trend?.trend_direction === 'increasing') return 'rose'
  if (trend?.trend_direction === 'decreasing') return 'fell'
  return 'showed no clear direction'
}

function describeVariable(variableId, lineups) {
  const cells = regions.map((region) => ({
    region: shortName(region.name),
    trend: trendFor(lineups[region.id], variableId),
  })).filter((cell) => cell.trend)

  const significant = cells.filter((cell) => cell.trend.verdict === 'significant')
  if (!significant.length) {
    return 'No region separated a trend from noise in this record.'
  }

  const up = significant.filter((cell) => cell.trend.trend_direction === 'increasing').map((cell) => cell.region)
  const down = significant.filter((cell) => cell.trend.trend_direction === 'decreasing').map((cell) => cell.region)
  const quiet = cells.length - significant.length

  const parts = []
  if (up.length) parts.push(`rose in ${listNames(up)}`)
  if (down.length) parts.push(`fell in ${listNames(down)}`)

  return `${significant.length} of ${cells.length} regions: ${parts.join('; ')}${
    quiet ? `. The other ${quiet === 1 ? 'region' : `${quiet} regions`} showed no clear trend` : ''
  }.`
}

function lineupPeriod(lineup) {
  const starts = (lineup?.rows ?? []).map((row) => row.period_start).filter(Boolean).sort()
  const ends = (lineup?.rows ?? []).map((row) => row.period_end).filter(Boolean).sort()
  if (!starts.length || !ends.length) return null
  return `${starts[0].slice(0, 4)}–${ends.at(-1).slice(0, 4)}`
}

function movementClusters(lineups) {
  return regions
    .map((region) => {
      const moves = significantMoves(lineups[region.id])
      const up = moves.filter((move) => move.trend.trend_direction === 'increasing').map((move) => move.label)
      const down = moves.filter((move) => move.trend.trend_direction === 'decreasing').map((move) => move.label)
      return { region: shortName(region.name), total: moves.length, up, down }
    })
    .filter((cluster) => cluster.total >= 3)
}

function significantMoves(lineup) {
  return variables
    .map((variable) => {
      const row = lineup?.rows?.find((item) => item.variable_id === variable.id)
      return row && row.trend?.verdict === 'significant'
        ? { label: row.label || variable.fallbackLabel, trend: row.trend }
        : null
    })
    .filter(Boolean)
}

function SummaryPage() {
  const { data: ireland, loading: irelandLoading, error: irelandError } = useData('lineup', { regionId: 'ireland' })
  const { data: iberia, loading: iberiaLoading, error: iberiaError } = useData('lineup', { regionId: 'iberia' })
  const { data: sahel, loading: sahelLoading, error: sahelError } = useData('lineup', { regionId: 'sahel' })
  const { data: nwSouthAsia, loading: nwLoading, error: nwError } = useData('lineup', { regionId: 'nw_south_asia' })
  const { data: usSouthwest, loading: usLoading, error: usError } = useData('lineup', { regionId: 'us_southwest' })

  const loadedLineups = useMemo(
    () => [ireland, iberia, sahel, nwSouthAsia, usSouthwest],
    [ireland, iberia, sahel, nwSouthAsia, usSouthwest],
  )
  const { lineups: windowedList, pending: windowPending, startYear, endYear } = useWindowedLineups(loadedLineups)
  const lineups = {
    ireland: windowedList[0],
    iberia: windowedList[1],
    sahel: windowedList[2],
    nw_south_asia: windowedList[3],
    us_southwest: windowedList[4],
  }
  const isWindowed = windowedList.some((lineup) => lineup?.windowed)
  const loading = irelandLoading || iberiaLoading || sahelLoading || nwLoading || usLoading || windowPending
  const error = irelandError || iberiaError || sahelError || nwError || usError

  const labels = variables.reduce((map, variable) => {
    const row = Object.values(lineups)
      .flatMap((lineup) => lineup?.rows ?? [])
      .find((item) => item.variable_id === variable.id)
    map[variable.id] = row?.label || variable.fallbackLabel
    return map
  }, {})

  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>Summary</h1>
          <p>
            Five signals across five regions, read from supplied results: what changed over the
            measured period, and what moved alongside it.
          </p>
        </div>
        <Link className="button button-secondary" to="/explore">Open the Lineup</Link>
      </div>

      <SampleDataWarning />

      {loading && <LoadingState label="Loading supplied regional summaries" />}
      {error && <ErrorState message={error.message} />}

      {!loading && !error && (
        <>
          <Panel title="The short answer">
            <div className="summary-answer">
              <div className="summary-answer-column">
                <span className="section-index">What changed</span>
                <ul className="summary-list">
                  {variables.map((variable) => (
                    <li key={variable.id}>
                      <strong>{labels[variable.id]}</strong> — {describeVariable(variable.id, lineups)}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="summary-answer-column">
                <span className="section-index">Because of that change, what changed?</span>
                <p className="summary-plain">
                  This snapshot cannot answer &ldquo;because&rdquo;. Each signal is tested on its own
                  record, and TerraLens does not run an attribution test, so no variable here is
                  evidence that another one caused it to move.
                </p>
                <p className="summary-plain">
                  What it can show is what moved at the same time in the same place. These regions
                  had three or more signals separate a trend from noise:
                </p>
                <ul className="summary-list summary-clusters">
                  {movementClusters(lineups).map((cluster) => (
                    <li key={cluster.region}>
                      <strong>{cluster.region}</strong>
                      {cluster.up.length ? ` — rose: ${listNames(cluster.up)}` : ''}
                      {cluster.down.length ? `${cluster.up.length ? ';' : ' —'} fell: ${listNames(cluster.down)}` : ''}.
                    </li>
                  ))}
                </ul>
                <p className="summary-plain">
                  Read that as a record of simultaneous movement, not a chain of effects.
                </p>
                <p className="summary-caution">
                  Co-movement is not cause. A shared direction may reflect the same large-scale
                  climate pattern, a shared input dataset, or coincidence.
                </p>
              </div>
            </div>
          </Panel>

          <Panel title="All five signals, all five regions" meta="Adjusted verdicts" flush>
            <div className="summary-table-wrap">
              <table className="summary-table">
                <thead>
                  <tr>
                    <th scope="col">Signal</th>
                    {regions.map((region) => (
                      <th scope="col" key={region.id}>{shortName(region.name)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {variables.map((variable) => (
                    <tr key={variable.id}>
                      <th scope="row" className="summary-signal">
                        {labels[variable.id]}
                        <span>{unitPerDecade(trendFor(lineups.ireland, variable.id))}</span>
                      </th>
                      {regions.map((region) => {
                        const trend = trendFor(lineups[region.id], variable.id)
                        return (
                          <td key={region.id}>
                            {trend ? (
                              <Link
                                className="summary-cell"
                                to={`/explore/${variable.id}?region=${region.id}`}
                                aria-label={`${labels[variable.id]} in ${region.name}: ${verdictLabel(trend.verdict)}`}
                              >
                                <VerdictBadge verdict={trend.verdict} />
                                <span className="summary-slope">{slopePerDecade(trend)}</span>
                              </Link>
                            ) : (
                              <span className="summary-slope">{isWindowed ? 'Not offered' : 'Not supplied'}</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="summary-footnote">
              {isWindowed
                ? <>Slopes are Sen&rsquo;s slope per decade for the window {startYear}&ndash;{endYear} (air
                  temperature starts in 1981), read from the supplied precomputed windows. </>
                : <>Slopes are Sen&rsquo;s slope per decade for the supplied record (1981&ndash;2025 for
                  air temperature, 1980&ndash;2025 for the other signals). </>}
              Verdicts use the
              Benjamini&ndash;Hochberg adjusted p-value; &ldquo;no clear trend&rdquo; means the test
              could not separate a trend from noise, not that nothing changed.
            </p>
          </Panel>

          <Panel title="What moved alongside, region by region">
            <div className="summary-region-grid">
              {regions.map((region) => {
                const lineup = lineups[region.id]
                const moves = significantMoves(lineup)
                const period = lineupPeriod(lineup)
                return (
                  <article className="summary-region-card" key={region.id}>
                    <div>
                      <h3>{shortName(region.name)}</h3>
                      {period && <p className="summary-period">{period}</p>}
                    </div>
                    {moves.length ? (
                      <ul className="summary-moves">
                        {moves.map((move) => (
                          <li key={move.label}>
                            <span>{move.label} {directionVerb(move.trend)}</span>
                            <strong>{slopePerDecade(move.trend)}</strong>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="summary-plain">No signal separated a trend from noise here.</p>
                    )}
                    <p className="summary-note">
                      {moves.length} of {variables.length} signals separated a trend from noise.
                    </p>
                  </article>
                )
              })}
            </div>
          </Panel>
        </>
      )}
    </div>
  )
}

export default SummaryPage
