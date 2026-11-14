import { useCallback, useMemo, useState } from 'react'

import { useData } from '../hooks/useData.js'
import { FALLBACK_WINDOW, WindowContext } from './window.js'

const STORAGE_KEY = 'terralens-window-end'

function yearOf(value) {
  const year = Number(String(value ?? '').slice(0, 4))
  return Number.isFinite(year) && year > 0 ? year : null
}

function clamp(year, min, max) {
  return Math.min(Math.max(year, min), max)
}

function readStoredYear() {
  try {
    const stored = Number(window.localStorage.getItem(STORAGE_KEY))
    return Number.isFinite(stored) && stored > 0 ? stored : null
  } catch {
    return null
  }
}

function WindowProvider({ children }) {
  const { data: catalogue } = useData('catalogue')

  // The window the app can honestly describe runs from the earliest supplied
  // period start to the latest supplied period end.
  const bounds = useMemo(() => {
    const starts = (catalogue ?? []).map((item) => yearOf(item.period_start)).filter(Boolean)
    const ends = (catalogue ?? []).map((item) => yearOf(item.period_end)).filter(Boolean)
    if (!starts.length || !ends.length) return FALLBACK_WINDOW

    const start = Math.min(...starts)
    const end = Math.max(...ends)
    return end > start ? { start, end } : FALLBACK_WINDOW
  }, [catalogue])

  const [chosenEnd, setChosenEnd] = useState(readStoredYear)

  // A stored year from an older snapshot may sit outside today's bounds; the
  // displayed year is always clamped, and picking a year rewrites the stored one.
  const endYear = clamp(chosenEnd ?? bounds.end, bounds.start, bounds.end)

  const setEndYear = useCallback((year) => {
    const next = clamp(Number(year), bounds.start, bounds.end)
    setChosenEnd(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, String(next))
    } catch {
      // A blocked storage write only costs persistence, never correctness.
    }
  }, [bounds.start, bounds.end])

  const value = useMemo(
    () => ({ startYear: bounds.start, endYear, maxYear: bounds.end, setEndYear }),
    [bounds.start, bounds.end, endYear, setEndYear],
  )

  return <WindowContext.Provider value={value}>{children}</WindowContext.Provider>
}

export default WindowProvider
