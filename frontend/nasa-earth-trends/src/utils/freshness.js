const DAY_MS = 86400000

// The exported version carries its build date: terralens-2026-11-14.
export function snapshotDateFrom(version) {
  const match = typeof version === 'string' ? version.match(/(\d{4}-\d{2}-\d{2})/) : null
  if (!match) return null

  const date = new Date(`${match[1]}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

// A snapshot rebuilt this week is fresh; one that has not moved in months is
// worth flagging, because the numbers may predate a newer NASA reprocessing.
export function freshnessOf(date, now = new Date()) {
  if (!date) return { tone: 'unknown', label: 'No snapshot', ageDays: null }

  const ageDays = Math.max(0, Math.floor((now.getTime() - date.getTime()) / DAY_MS))
  const tone = ageDays <= 45 ? 'fresh' : ageDays <= 120 ? 'aging' : 'stale'
  const label = tone === 'fresh' ? 'Fresh' : tone === 'aging' ? 'Aging' : 'Stale'

  return { tone, label, ageDays }
}

export function ageLabel(ageDays) {
  if (ageDays == null) return '—'
  if (ageDays === 0) return 'Today'
  if (ageDays === 1) return 'Yesterday'
  return `${ageDays} days ago`
}

// The newest observation the catalogue describes, e.g. "Dec 2025".
export function coverageEndFrom(catalogue) {
  const ends = (catalogue ?? [])
    .map((item) => item?.period_end)
    .filter((value) => typeof value === 'string' && /^\d{4}-\d{2}/.test(value))
    .sort()

  const last = ends.at(-1)
  if (!last) return null

  const [year, month] = last.split('-')
  const label = new Date(Date.UTC(Number(year), Number(month) - 1, 1))
    .toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })

  return `${label} ${year}`
}
