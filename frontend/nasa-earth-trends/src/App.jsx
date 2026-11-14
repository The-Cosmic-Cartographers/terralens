import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import earthIcon from './assets/earthicon.png';
import WindowSelector from './components/WindowSelector.jsx'
import { useData } from './hooks/useData.js'

import './App.css'

const navigation = [
  { to: '/', label: 'Overview', end: true, icon: 'overview', title: 'Overview' },
  { to: '/explore', label: 'The Lineup', icon: 'lineup', title: 'The Lineup' },
  { to: '/compare', label: 'Opposite Trends', icon: 'compare', title: 'Opposite Trends' },
  { to: '/case-files', label: 'Case Files', icon: 'cases', title: 'Case Files' },
]

const iconPaths = {
  overview: 'M3 3h7v7H3zM14 3h7v4h-7zM14 10h7v11h-7zM3 13h7v8H3z',
  lineup: 'M4 5h16M4 10h16M4 15h10M4 20h6',
  compare: 'M7 4 3 8l4 4M3 8h14M17 12l4 4-4 4M21 16H7',
  cases: 'M5 3h10l4 4v14H5zM14 3v5h5M8 13h8M8 17h6',
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

function currentTitle(pathname) {
  if (pathname.startsWith('/explore/')) return 'The Lineup / Trend detail'
  const match = navigation.find((item) =>
    item.end ? pathname === item.to : pathname.startsWith(item.to),
  )
  return match?.title ?? 'TerraLens'
}

function App() {
  const location = useLocation()
  const [theme, setTheme] = useState(readTheme)
  const { data: health, error, mode } = useData('health')
  const online = Boolean(health) && !error

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
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="side-status">
          <span className="side-label">Data status</span>
          <div className="side-status-row">
            <span className={online ? 'status-dot' : 'status-dot status-off'} />
            {online ? 'Snapshot ready' : error ? 'Snapshot unavailable' : 'Checking…'}
          </div>
          <dl>
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

        <p className="side-note">
          Independent team project for the NASA Space Apps Challenge 2026. Not
          an official NASA product.
        </p>
      </aside>

      <div className="dash-main">
        <header className="topbar">
          <div className="crumbs">
            <span>TerraLens</span>
            <span aria-hidden="true">/</span>
            <strong>{currentTitle(location.pathname)}</strong>
          </div>
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
        </header>

        <main className="workspace" key={location.pathname}>
          <Outlet />
        </main>

        <footer className="workspace-foot">
          <span>Data: NASA GES DISC (MERRA-2, GLDAS), GPM IMERG, Earthdata</span>
          <span>Evidence over assumptions. No forecasts, no causes.</span>
        </footer>
      </div>
    </div>
  )
}

export default App
