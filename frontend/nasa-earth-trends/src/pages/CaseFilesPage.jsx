import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState.jsx'
import ErrorState from '../components/ErrorState.jsx'
import LoadingState from '../components/LoadingState.jsx'
import Panel from '../components/Panel.jsx'
import SampleDataWarning from '../components/SampleDataWarning.jsx'
import SourceLink from '../components/SourceLink.jsx'
import VerdictBadge from '../components/VerdictBadge.jsx'
import { datasetSourceUrl } from '../data/sources.js'
import { useData } from '../hooks/useData.js'

const DATASET_ID = 'merra2_m2tmnxslv'

const caseFiles = [
  {
    id: 'warming-rate',
    number: '01',
    title: 'Is everywhere warming at the same speed?',
    question: 'Compare one supplied variable across three places without turning a regional comparison into a global ranking.',
    caveat: 'These are three boxes of different size and climate, not a global ranking. A faster rate here does not mean this is the fastest-warming place on Earth.',
    regionId: 'us_southwest',
    compare: true,
  },
  {
    id: 'window-verdict',
    number: '02',
    title: 'Can the same place look flat?',
    question: 'See how the verdict changes when the supplied time window changes.',
    caveat: 'No clear trend means this window cannot separate a trend from noise. It does not mean the place stopped changing.',
    regionId: 'ireland',
    compare: false,
  },
  {
    id: 'sahel-shape',
    number: '03',
    title: 'Where does the Sahel record split?',
    question: 'Distinguish the overall trend from a descriptive diagnostic about the shape of a record.',
    caveat: 'The change point is descriptive. It says nothing about what caused it and does not predict what happens next.',
    regionId: 'sahel',
    compare: false,
  },
]

const steps = ['Question', 'Lineup row', 'Detail chart', 'Compare']

function formatSlope(result) {
  if (result?.sen_slope_per_year == null) return '—'
  return `${(Number(result.sen_slope_per_year) * 10).toFixed(2)} ${result.unit_per_year?.replace('/yr', '/decade') || 'per decade'}`
}

function formatInterval(result) {
  return result?.confidence_interval_95?.map((value) => Number(value).toFixed(2)).join(' to ') || '—'
}

function ResultSummary({ result }) {
  if (!result) {
    return <EmptyState title="Case result unavailable" message="This case file is waiting for the corresponding supplied result export." />
  }

  if (result.trend_direction === 'withheld' || result.withheld_reason) {
    return <EmptyState title="Result withheld" message={result.withheld_reason || 'The supplied result did not meet the coverage rules.'} />
  }

  return (
    <div className="case-evidence">
      <div><span>Rate</span><strong>{formatSlope(result)}</strong></div>
      <div><span>95% interval</span><strong>{formatInterval(result)}</strong></div>
      <div><span>Adjusted p</span><strong>{result.adjusted_p_value ?? '—'}</strong></div>
        <div><span>Period</span><strong>{result.period_start ? `${result.period_start} – ${result.period_end}` : `${result.start} – ${result.end}`}</strong></div>
      <VerdictBadge verdict={result.verdict} />
    </div>
  )
}

function CaseFilesPage() {
  const [caseIndex, setCaseIndex] = useState(0)
  const [stepIndex, setStepIndex] = useState(0)
  const currentCase = caseFiles[caseIndex]
  const { data: compare, loading: compareLoading, error: compareError } = useData('compare', { datasetId: DATASET_ID })
  const { data: irelandLineup, loading: irelandLoading } = useData('lineup', { regionId: 'ireland' })
  const { data: sahelLineup, loading: sahelLoading, error: sahelError } = useData('lineup', { regionId: 'sahel' })
  const { data: irelandWindows } = useData('windows', { regionId: 'ireland', datasetId: DATASET_ID })

  const irelandResult = irelandLineup?.rows?.find((row) => row.variable_id === 't2m')?.trend
  const sahelResult = sahelLineup?.rows?.find((row) => row.variable_id === 't2m')?.trend
  const usResult = compare?.results?.find((row) => row.region_id === 'us_southwest')
  const compareResults = compare?.results || []
  const shortWindow = irelandWindows?.windows?.find((window) => window.start === 1986 && window.end === 2015)
  const caseResult = currentCase.id === 'warming-rate'
    ? usResult
    : currentCase.id === 'window-verdict'
      ? shortWindow
      : sahelResult
  const loading = currentCase.id === 'warming-rate'
    ? compareLoading
    : currentCase.id === 'window-verdict'
      ? irelandLoading
      : sahelLoading
  const error = currentCase.id === 'warming-rate' ? compareError : sahelError

  const changePoint = useMemo(() => sahelResult?.change_point, [sahelResult])

  function selectCase(index) {
    setCaseIndex(index)
    setStepIndex(0)
  }

  return (
    <div className="page">
      <div className="page-title">
        <div>
          <h1>Case Files</h1>
          <p>Three worked investigations built from supplied results, with the caveats kept next to the claim.</p>
        </div>
      </div>

      <SampleDataWarning />

      <div className="case-selector" role="tablist" aria-label="Case files">
        {caseFiles.map((item, index) => (
          <button
            key={item.id}
            className={index === caseIndex ? 'case-tab active' : 'case-tab'}
            type="button"
            role="tab"
            aria-selected={index === caseIndex}
            onClick={() => selectCase(index)}
          >
            <span>{item.number}</span>
            {item.title}
          </button>
        ))}
      </div>

      <Panel className="case-file-panel" title={`${currentCase.number} · ${currentCase.title}`}>
        <p className="case-question">{currentCase.question}</p>
        <div className="case-stepper" role="tablist" aria-label="Case file steps">
          {steps.map((step, index) => (
            <button
              key={step}
              type="button"
              className={index === stepIndex ? 'case-step active' : 'case-step'}
              aria-selected={index === stepIndex}
              onClick={() => setStepIndex(index)}
            >
              <span>{index + 1}</span>{step}
            </button>
          ))}
        </div>

        {loading ? <LoadingState label="Loading supplied case result" /> : error ? <ErrorState message={error.message} /> : (
          <div className="case-step-content">
            {stepIndex === 0 && (
              <div className="case-copy-block">
                <span className="section-index">THE QUESTION</span>
                <h2>{currentCase.question}</h2>
                <p>TerraLens starts with a question, then points to the relevant Lineup row and detail record. The answer is limited to the supplied period and product.</p>
              </div>
            )}

            {stepIndex === 1 && (
              <div>
                <span className="section-index">THE LINEUP ROW</span>
                <h2>Air temperature (2 m)</h2>
                <p className="case-muted">
                  <SourceLink href={datasetSourceUrl(DATASET_ID)}>MERRA-2 model reanalysis</SourceLink>
                  {' · monthly series · 1981–2025'}
                </p>
                <ResultSummary result={caseResult} />
                <Link className="button button-secondary" to={`/explore?region=${currentCase.regionId}&variable=t2m`}>Open this Lineup view</Link>
              </div>
            )}

            {stepIndex === 2 && (
              <div>
                <span className="section-index">THE DETAIL RECORD</span>
                <h2>Read the measured series and supplied method</h2>
                <p>The detail view carries the monthly series, period, source, coverage and precomputed trend statistics. The browser does not recalculate the result.</p>
                <Link className="button button-secondary" to={`/explore/t2m?region=${currentCase.regionId}&dataset=${DATASET_ID}`}>Open detail chart</Link>
              </div>
            )}

            {stepIndex === 3 && (
              <div>
                <span className="section-index">THE COMPARISON</span>
                {currentCase.compare ? (
                  <>
                    <h2>Same variable, different regional records</h2>
                    <div className="case-compare-strip">
                      {compareResults.map((result) => <ResultSummary result={result} key={result.region_id} />)}
                    </div>
                    <Link className="button button-secondary" to="/compare">Open Opposite Trends</Link>
                  </>
                ) : currentCase.id === 'window-verdict' ? (
                  <>
                    <h2>Full record versus a shorter supplied window</h2>
                    <ResultSummary result={irelandResult} />
                    <ResultSummary result={shortWindow} />
                    <Link className="button button-secondary" to={`/explore/t2m?region=ireland&dataset=${DATASET_ID}`}>Open Time Machine</Link>
                  </>
                ) : (
                  <>
                    <h2>Trend direction and record shape are different questions</h2>
                    <ResultSummary result={sahelResult} />
                    <div className="case-diagnostic"><span>Descriptive split year</span><strong>{changePoint?.change_point_year ?? '—'}</strong><span>Mean before / after</span><strong>{changePoint ? `${Number(changePoint.mean_before).toFixed(2)} / ${Number(changePoint.mean_after).toFixed(2)} °C` : '—'}</strong></div>
                    <Link className="button button-secondary" to={`/explore/t2m?region=sahel&dataset=${DATASET_ID}`}>Open Sahel detail</Link>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        <aside className="case-caveat"><strong>Caveat</strong><span>{currentCase.caveat}</span></aside>
      </Panel>
    </div>
  )
}

export default CaseFilesPage
