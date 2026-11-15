import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

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
  const [searchParams, setSearchParams] = useSearchParams()

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

  // The URL wins over the stored preference: a shared link should open on the
  // range it names, and back/forward should restore it without a write.
  const urlEnd = yearOf(searchParams.get('end'))
  const requestedStart = yearOf(searchParams.get('start'))
  const [chosenEnd, setChosenEnd] = useState(readStoredYear)

  const endYear = urlEnd == null
    ? clamp(chosenEnd ?? bounds.end, bounds.start, bounds.end)
    : clamp(urlEnd, bounds.start, bounds.end)
  const startYear = clamp(requestedStart ?? bounds.start, bounds.start, endYear)

  const setEndYear = useCallback((year) => {
    const next = clamp(Number(year), bounds.start, bounds.end)
    setChosenEnd(next)

    setSearchParams((params) => {
      const updated = new URLSearchParams(params)
      updated.set('end', String(next))

      // A requested start later than the chosen end would leave the plot empty,
      // so that request is dropped and the record's own start applies again.
      const requested = yearOf(updated.get('start'))
      if (requested != null && requested >= next) updated.delete('start')

      return updated
    }, { replace: true })
  }, [bounds.start, bounds.end, setSearchParams, setChosenEnd])

  // Whatever the range ends up being, the next visit without a URL keeps it.
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(endYear))
    } catch {
      // A blocked storage write only costs persistence, never correctness.
    }
  }, [endYear])

  const value = useMemo(
    () => ({
      startYear,
      endYear,
      minYear: bounds.start,
      maxYear: bounds.end,
      setEndYear,
    }),
    [startYear, bounds.start, bounds.end, endYear, setEndYear],
  )

  return <WindowContext.Provider value={value}>{children}</WindowContext.Provider>
}

export default WindowProvider
