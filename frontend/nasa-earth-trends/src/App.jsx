import { Suspense, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import earthIcon from './assets/earthicon.png';
import LoadingState from './components/LoadingState.jsx'
import WindowSelector from './components/WindowSelector.jsx'
import { useBusy } from './hooks/useBusy.js'
import { useData } from './hooks/useData.js'
import { ageLabel, coverageEndFrom, freshnessOf, snapshotDateFrom } from './utils/freshness.js'

import './App.css'

// Each hint says what the page is for, so a first visit knows where to go.
const navigation = [
  { to: '/', label: 'Overview', end: true, icon: 'overview', title: 'Overview', hint: 'Start here' },
  { to: '/summary', label: 'Summary', icon: 'summary', title: 'Summary', hint: 'Every region at a glance' },
  { to: '/explore', label: 'The Lineup', icon: 'lineup', title: 'The Lineup', hint: 'Ranked signals per region' },
  { to: '/compare', label: 'Opposite Trends', icon: 'compare', title: 'Opposite Trends', hint: 'Two places side by side' },
]

const iconPaths = {
  overview: 'M3 3h7v7H3zM14 3h7v4h-7zM14 10h7v11h-7zM3 13h7v8H3z',
  summary: 'M4 5h7v6H4zM13 5h7v6h-7zM4 13h7v6H4zM13 13h7v6h-7z',
  lineup: 'M4 5h16M4 10h16M4 15h10M4 20h6',
  compare: 'M7 4 3 8l4 4M3 8h14M17 12l4 4-4 4M21 16H7',
}

function NavIcon({ name }) {
  return (
    <svg
      className="nav-icon"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="square"
      aria-hidden="true"
    >
      <path d={iconPaths[name]} />
    </svg>
  )
}

const THEME_KEY = 'terralens-theme'
// Earlier builds saved the theme on first paint, so a stored value alone does
// not prove the visitor chose it. Only a toggle sets this marker.
const THEME_CHOICE_KEY = 'terralens-theme-chosen'

function readTheme() {
  try {
    const chosen = window.localStorage.getItem(THEME_CHOICE_KEY)
    const stored = window.localStorage.getItem(THEME_KEY)
    if (chosen && (stored === 'light' || stored === 'dark')) return stored
  } catch {
    // Blocked storage only costs a preference, never the page.
  }

  return 'light'
}

// Breadcrumb trail after "TerraLens". Every step but the current page links.
function crumbsFor(pathname) {
  if (pathname.startsWith('/explore/')) {
    return [{ label: 'The Lineup', to: '/explore' }, { label: 'Trend detail' }]
  }
  const match = navigation.find((item) =>
    item.end ? pathname === item.to : pathname.startsWith(item.to),
  )
  return [{ label: match?.title ?? 'TerraLens' }]
}

function App() {
  const location = useLocation()
  const [theme, setTheme] = useState(readTheme)
  const busy = useBusy()
  const crumbs = crumbsFor(location.pathname)
  const { data: health, error, mode } = useData('health')
  const { data: catalogue } = useData('catalogue')
  const online = Boolean(health) && !error
  const freshness = freshnessOf(snapshotDateFrom(health?.data_version))
  const coverageEnd = coverageEndFrom(catalogue)

  // Mirror the theme onto <html> so the page body, scrollbars and native
  // controls take the same tokens as the dashboard.
  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    try {
      window.localStorage.setItem(THEME_KEY, next)
      window.localStorage.setItem(THEME_CHOICE_KEY, '1')
    } catch {
      // Blocked storage only costs a preference, never the page.
    }
  }

  return (
    <div className={`dash theme-${theme}`}>
      <aside className="sidebar">
        <NavLink className="brand" to="/" aria-label="TerraLens overview">
        <img
          src={earthIcon}
          alt="TerraLens"
          className="brand-mark"
        />
          <span>
            <strong>TerraLens</strong>
            <small>Earth system trend detective</small>
          </span>
        </NavLink>

        <nav className="side-nav" aria-label="Primary navigation">
          <span className="side-label">Investigate</span>
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className="nav-link"
            >
              <NavIcon name={item.icon} />
              <span className="nav-text">
                <span>{item.label}</span>
                <small className="nav-hint">{item.hint}</small>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="side-status">
          <span className="side-label">Data freshness</span>
          <div className="side-status-row">
            <span
              className={`status-dot status-${online ? freshness.tone : 'off'}`}
              title={online ? `Snapshot rebuilt ${ageLabel(freshness.ageDays).toLowerCase()}` : undefined}
            />
            {online ? freshness.label : error ? 'Snapshot unavailable' : 'Checking…'}
          </div>
          <dl>
            <div>
              <dt>Updated</dt>
              <dd>{online ? ageLabel(freshness.ageDays) : '—'}</dd>
            </div>
            <div>
              <dt>Coverage</dt>
              <dd>{coverageEnd ?? '—'}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{health?.data_version ?? '—'}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{mode === 'static' ? 'Static snapshot' : 'Live API'}</dd>
            </div>
          </dl>
        </div>

      </aside>

      <div className="dash-main">
        <header className="topbar">
          <nav className="crumbs" aria-label="Breadcrumb">
            <Link to="/">TerraLens</Link>
            {crumbs.map((crumb, index) => (
              <span key={crumb.label} className="crumb-step">
                <span aria-hidden="true">/</span>
                {index < crumbs.length - 1
                  ? <Link to={crumb.to}>{crumb.label}</Link>
                  : <strong aria-current="page">{crumb.label}</strong>}
              </span>
            ))}
          </nav>
          <div className="topbar-chips">
            <button
              className="theme-toggle"
              type="button"
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              aria-pressed={theme === 'light'}
              onClick={toggleTheme}
            >
              <span className="theme-toggle-track" aria-hidden="true">
                <span className="theme-toggle-thumb" />
              </span>
              <span className="theme-toggle-label">
                {theme === 'dark' ? 'Dark mode' : 'Light mode'}
              </span>
            </button>
            <WindowSelector />
          </div>
          <div className={busy ? 'progress-bar is-busy' : 'progress-bar'} aria-hidden="true">
            <span />
          </div>
        </header>

        <main className="workspace" key={location.pathname}>
          <Suspense fallback={<LoadingState label="Loading evidence" />}>
            <Outlet />
          </Suspense>
        </main>

        <footer className="workspace-foot">
          <span>
            Data:{' '}
            <a className="source-link" href="https://disc.gsfc.nasa.gov" target="_blank" rel="noreferrer noopener">NASA GES DISC</a>
            {' ('}
            <a className="source-link" href="https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/" target="_blank" rel="noreferrer noopener">MERRA-2</a>
            {', '}
            <a className="source-link" href="https://disc.gsfc.nasa.gov/datasets/OMNO2D_004/summary" target="_blank" rel="noreferrer noopener">OMI</a>
            {'), '}
            <a className="source-link" href="https://www.earthdata.nasa.gov" target="_blank" rel="noreferrer noopener">Earthdata</a>
          </span>
          <span>Evidence over assumptions. No forecasts, no causes.</span>
        </footer>
      </div>
    </div>
  )
}

export default App
