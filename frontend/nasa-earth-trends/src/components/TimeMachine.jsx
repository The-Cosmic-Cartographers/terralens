import { useMemo, useState } from 'react'

import EmptyState from './EmptyState.jsx'
import ErrorState from './ErrorState.jsx'
import LoadingState from './LoadingState.jsx'
import VerdictBadge from './VerdictBadge.jsx'
import { useData } from '../hooks/useData.js'
import { formatP, formatSlope } from '../utils/format.js'

function TimeMachine({ regionId, datasetId, headline = null }) {
  const { data, loading, error } = useData('windows', { regionId, datasetId })
  const [start, setStart] = useState(null)
  const [end, setEnd] = useState(null)

  const bounds = useMemo(() => {
    if (!data?.windows?.length) return null

    return {
      min: Math.min(...data.windows.map((item) => item.start)),
      max: Math.max(...data.windows.map((item) => item.end)),
    }
  }, [data])

  const effectiveStart = start ?? bounds?.min
  const effectiveEnd = end ?? bounds?.max
  const selected = data?.windows?.find(
    (item) => item.start === effectiveStart && item.end === effectiveEnd,
  )

  // The full period is the headline result: show the same numbers as the Trend
  // result panel, never a second p-value for the same record.
  const isFullPeriod = Boolean(selected) && selected.start === bounds?.min && selected.end === bounds?.max
  const shown = isFullPeriod && headline
    ? {
        ...selected,
        verdict: headline.verdict,
        sen_slope_per_year: headline.sen_slope_per_year,
        adjusted_p_value: headline.adjusted_p_value,
      }
    : selected

  if (loading) return <LoadingState label="Loading precomputed windows" />
  if (error) return <ErrorState message={error.message} />
  if (!data?.windows?.length || !bounds) {
    return (
      <EmptyState
        title="Time Machine unavailable"
        message="No precomputed windows were supplied for this result."
      />
    )
  }

  return (
    <section className="time-machine">
      <div className="time-machine-heading">
        <div>
          <h2>Change the window, not the evidence.</h2>
          <p>Both sliders read supplied windows; the browser does not recalculate statistics.</p>
          <p>
            Windows shorter than {data.min_window_years} years are not offered: a p-value from a
            shorter record would overstate confidence, so none is reported.
          </p>
        </div>
        <span className="window-rule">Minimum: {data.min_window_years} years</span>
      </div>

      <div className="range-controls">
        <label>
          <span>Start year</span>
          <input
            type="range"
            min={bounds.min}
            max={Math.max(bounds.min, effectiveEnd - data.min_window_years + 1)}
            value={effectiveStart}
            onChange={(event) => setStart(Number(event.target.value))}
          />
          <strong>{effectiveStart}</strong>
        </label>
        <label>
          <span>End year</span>
          <input
            type="range"
            min={Math.min(bounds.max, effectiveStart + data.min_window_years - 1)}
            max={bounds.max}
            value={effectiveEnd}
            onChange={(event) => setEnd(Number(event.target.value))}
          />
          <strong>{effectiveEnd}</strong>
        </label>
      </div>

      {shown ? (
        <div className="window-result">
          <div><span>Selected window</span><strong>{shown.start} — {shown.end}</strong></div>
          <VerdictBadge verdict={shown.verdict} />
          <div><span>Sen slope / year</span><strong>{formatSlope(shown.sen_slope_per_year)}</strong></div>
          <div><span>{isFullPeriod ? 'Adjusted p-value' : 'Window p-value'}</span><strong>{formatP(shown.adjusted_p_value)}</strong></div>
        </div>
      ) : (
        <div className="window-result window-result-empty">
          This exact window is not present in the supplied results.
        </div>
      )}
    </section>
  )
}

export default TimeMachine
