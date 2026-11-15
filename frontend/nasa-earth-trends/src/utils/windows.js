// Re-reading the Lineup for a chosen window. The browser never recalculates a
// statistic: every number comes from the precomputed `windows/<dataset>/<region>`
// files (every start/end pair at least ten years apart, adjusted across the five
// variables for that same window), and a row falls back to its full-record result
// when the window covers the whole record.

// D6: no p-value is reported for a record shorter than this.
export const MIN_WINDOW_YEARS = 10

function yearOf(value) {
  const year = Number(String(value ?? '').slice(0, 4))
  return Number.isFinite(year) && year > 0 ? year : null
}

// The part of the chosen window a row's own record can cover.
export function rowWindow(row, startYear, endYear) {
  const recordStart = yearOf(row.trend?.period_start ?? row.period_start)
  const recordEnd = yearOf(row.trend?.period_end ?? row.period_end)
  if (recordStart == null || recordEnd == null) return null

  const start = Math.max(startYear, recordStart)
  const end = Math.min(endYear, recordEnd)
  return { start, end, full: start === recordStart && end === recordEnd }
}

function directionOf(verdict, slope) {
  if (verdict !== 'significant' || slope == null || slope === 0) return 'no_significant_trend'
  return slope > 0 ? 'increasing' : 'decreasing'
}

// One Lineup row for the chosen window, or the same row marked as not offered.
export function applyWindow(row, windowsFile, startYear, endYear) {
  const span = rowWindow(row, startYear, endYear)
  if (!span || span.full) return row

  const found = windowsFile?.windows?.find((item) => item.start === span.start && item.end === span.end)
  if (!found) {
    return { ...row, window_unavailable: true, window_span: span }
  }

  const trend = {
    ...row.trend,
    sen_slope_per_year: found.sen_slope_per_year,
    confidence_interval_95: found.confidence_interval_95,
    p_value: found.p_value,
    adjusted_p_value: found.adjusted_p_value,
    verdict: found.verdict,
    trend_direction: directionOf(found.verdict, found.sen_slope_per_year),
    period_start: `${found.start}-01-01`,
    period_end: `${found.end}-12-01`,
  }

  return { ...row, trend, period_start: trend.period_start, period_end: trend.period_end, window_span: span }
}

// A whole lineup for the chosen window. When every row is the full record the
// lineup's own ranking stands; otherwise rows are ranked by the window's adjusted
// p (rows with no window last), keeping the lineup order for ties.
export function windowedLineup(lineup, windowsByKey, startYear, endYear) {
  if (!lineup?.rows) return lineup

  const rows = lineup.rows.map((row) => (
    applyWindow(row, windowsByKey[`${lineup.region_id}|${row.dataset_id}`], startYear, endYear)
  ))
  if (rows.every((row, index) => row === lineup.rows[index])) return lineup

  const ranked = rows
    .map((row, index) => ({ row, index }))
    .sort((a, b) => {
      const pa = a.row.window_unavailable ? Infinity : (a.row.trend?.adjusted_p_value ?? Infinity)
      const pb = b.row.window_unavailable ? Infinity : (b.row.trend?.adjusted_p_value ?? Infinity)
      return pa - pb || a.index - b.index
    })
    .map((item) => item.row)

  return { ...lineup, rows: ranked, windowed: true }
}

// Which windows files a set of lineups needs for the chosen window.
export function neededWindows(lineups, startYear, endYear) {
  const needed = []
  for (const lineup of lineups) {
    for (const row of lineup?.rows ?? []) {
      const span = rowWindow(row, startYear, endYear)
      if (span && !span.full) needed.push({ regionId: lineup.region_id, datasetId: row.dataset_id })
    }
  }
  return needed
}
