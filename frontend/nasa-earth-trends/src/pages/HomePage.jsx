import { Link } from 'react-router-dom'

import SampleDataWarning from '../components/SampleDataWarning.jsx'

function HomePage() {
  return (
    <div className="landing-page">
      <section className="hero-panel">
        <div className="eyebrow">
          <span className="eyebrow-line" />
          Earth observation, made legible
        </div>

        <h1>
          Find the signal
          <br />
          <em>inside the noise.</em>
        </h1>

        <p className="hero-copy">
          TerraLens helps you investigate long-term environmental change across
          contrasting regions—one measured trend at a time.
        </p>

        <div className="hero-actions">
          <Link className="button button-primary" to="/explore">
            Open the Lineup <span>↗</span>
          </Link>
          <Link className="text-link" to="/case-files">
            Read a case file <span>→</span>
          </Link>
        </div>

        <div className="hero-note">
          <span className="signal-icon">⌁</span>
          <span>
            <strong>Precomputed evidence.</strong> No forecasts. No claims
            about causes.
          </span>
        </div>
      </section>

      <section className="home-grid" aria-label="How TerraLens works">
        <div className="orbit-card card-dark">
          <span className="card-kicker">01 / Choose a place</span>
          <div className="orbit-art" aria-hidden="true">
            <span className="orbit orbit-one" />
            <span className="orbit orbit-two" />
            <span className="orbit-dot" />
          </div>
          <h2>Start with a region.</h2>
          <p>
            See what is changing where you live, or compare two places with
            different stories.
          </p>
        </div>

        <div className="orbit-card card-sand">
          <span className="card-kicker">02 / Scan the lineup</span>
          <div className="mini-bars" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
          <h2>Let the data point.</h2>
          <p>
            Five variables, ranked by their observed trend over the measured
            period.
          </p>
        </div>

        <div className="orbit-card card-coral">
          <span className="card-kicker">03 / Inspect the evidence</span>
          <div className="mini-chart" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <h2>Follow the trail.</h2>
          <p>
            Read the method, coverage, product source and uncertainty behind
            each result.
          </p>
        </div>
      </section>

      <SampleDataWarning />
    </div>
  )
}

export default HomePage
