import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { useWindow } from '../state/window.js'

// The pages that read the window. On the others the control would do nothing, so
// it says so instead of looking live.
function usesWindow(pathname) {
  return pathname.startsWith('/explore') || pathname.startsWith('/summary')
}

function WindowSelector() {
  const { startYear, endYear, maxYear, minEndYear, setEndYear } = useWindow()
  const { pathname } = useLocation()
  const applies = usesWindow(pathname)
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const listRef = useRef(null)

  // The list runs from the latest year down to the earliest end that still leaves
  // ten years for every row, so every option has a supplied result.
  const years = useMemo(
    () => Array.from({ length: maxYear - minEndYear + 1 }, (_, index) => maxYear - index),
    [minEndYear, maxYear],
  )

  useEffect(() => {
    if (!open || !applies) return undefined

    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }

    function onKeyDown(event) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open, applies])

  useEffect(() => {
    if (!open || !applies) return
    const selected = listRef.current?.querySelector('[aria-selected="true"]')
    selected?.scrollIntoView({ block: 'center' })
  }, [open, applies])

  return (
    <div className="window-selector" ref={rootRef}>
      <button
        type="button"
        className="chip window-selector-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={applies
          ? `Analysis window ${startYear} to ${endYear}. Choose an end year.`
          : `Analysis window ${startYear} to ${endYear}. It applies to The Lineup, Summary and Trend detail.`}
        title={applies ? undefined : 'The window applies to The Lineup, Summary and Trend detail'}
        disabled={!applies}
        onClick={() => setOpen((value) => !value)}
      >
        Window {startYear}–{endYear}
        <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true">
          <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      </button>

      {open && applies && (
        <div
          className="window-popover"
          role="listbox"
          aria-label="Analysis window end year"
          ref={listRef}
        >
          {years.map((year) => (
            <button
              key={year}
              type="button"
              role="option"
              aria-selected={year === endYear}
              className="window-option"
              onClick={() => {
                setEndYear(year)
                setOpen(false)
              }}
            >
              {year}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default WindowSelector
