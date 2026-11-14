import { NavLink, Outlet, useLocation } from 'react-router-dom'

import './App.css'

const navigation = [
  { to: '/', label: 'Home', end: true },
  { to: '/explore', label: 'The Lineup' },
  { to: '/compare', label: 'Opposite Trends' },
  { to: '/case-files', label: 'Case Files' },
]

function App() {
  const location = useLocation()

  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/" aria-label="TerraLens home">
          <span className="brand-mark" aria-hidden="true">
            TL
          </span>
          <span>
            <strong>TerraLens</strong>
            <small>Earth system trend detective</small>
          </span>
        </NavLink>

        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className="nav-link"
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="header-status">
          <span className="status-dot" />
          Snapshot ready
        </div>
      </header>

      <main className="page-container" key={location.pathname}>
        <Outlet />
      </main>

      <footer className="site-footer">
        <span>NASA Space Apps Challenge 2026</span>
        <span>Evidence over assumptions.</span>
      </footer>
    </div>
  )
}

export default App
