import { createContext, useContext } from 'react'

// The earliest and latest year the snapshot can describe. The provider replaces
// these with the real bounds from the catalogue as soon as it loads.
export const FALLBACK_WINDOW = { start: 1981, end: 2025 }

export const WindowContext = createContext({
  startYear: FALLBACK_WINDOW.start,
  endYear: FALLBACK_WINDOW.end,
  minYear: FALLBACK_WINDOW.start,
  maxYear: FALLBACK_WINDOW.end,
  setEndYear: () => {},
})

export function useWindow() {
  return useContext(WindowContext)
}
