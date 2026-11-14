import { useEffect, useMemo, useRef, useState } from 'react'

import { useWindow } from '../state/window.js'

function WindowSelector() {
  const { startYear, endYear, maxYear, setEndYear } = useWindow()
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const listRef = useRef(null)

  // The list always spans the whole record, so a year picked earlier can be
  // changed back without a reload.
  const years = useMemo(
    () => Array.from({ length: maxYear - startYear + 1 }, (_, index) => maxYear - index),
    [startYear, maxYear],
  )

  useEffect(() => {
    if (!open) return undefined

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
  }, [open])

  useEffect(() => {
    if (!open) return
    const selected = listRef.current?.querySelector('[aria-selected="true"]')
    selected?.scrollIntoView({ block: 'center' })
  }, [open])

  return (
    <div className="window-selector" ref={rootRef}>
      <button
        type="button"
        className="chip window-selector-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Analysis window ${startYear} to ${endYear}. Choose an end year.`}
        onClick={() => setOpen((value) => !value)}
      >
        Window {startYear}–{endYear}
        <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true">
          <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      </button>

      {open && (
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
