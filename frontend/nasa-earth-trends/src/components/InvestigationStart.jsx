import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DropdownMenu from './DropdownMenu.jsx'
import { regions } from '../data/regionOptions.js'
import { variableGlossary } from '../data/glossary.js'

const placeChoices = [
  ['maritime', 'Cool and maritime', 'ireland'],
  ['dry_summer', 'Dry-summer coast', 'iberia'],
  ['desert_edge', 'Desert edge and seasonal rain', 'sahel'],
  ['irrigated', 'Irrigated farmland and monsoon', 'nw_south_asia'],
  ['dryland', 'Dryland and water stress', 'us_southwest'],
]

const periodChoices = [
  ['full', 'Full available record', '1981', '2025'],
  ['recent', 'Recent 30-year window', '1996', '2025'],
  ['mid', 'A 30-year middle window', '1986', '2015'],
]

function InvestigationStart() {
  const navigate = useNavigate()
  const [placeType, setPlaceType] = useState(placeChoices[0][0])
  const [variableId, setVariableId] = useState(variableGlossary[0].variableId)
  const [period, setPeriod] = useState(periodChoices[0][0])

  function startInvestigation(event) {
    event.preventDefault()
    const regionId = placeChoices.find(([id]) => id === placeType)?.[2] || regions[0].id
    const selectedPeriod = periodChoices.find(([id]) => id === period) || periodChoices[0]
    const query = new URLSearchParams({
      region: regionId,
      variable: variableId,
      start: selectedPeriod[2],
      end: selectedPeriod[3],
    })
    navigate(`/explore?${query.toString()}`)
  }

  return (
    <section className="start-investigation" aria-labelledby="start-investigation-title">
      <div>
        <span className="section-index">Start an investigation</span>
        <h2 id="start-investigation-title">Ask a smaller question. See the evidence faster.</h2>
        <p>Choose the kind of place, the signal you care about, and the period you want to inspect. These choices filter the Lineup; they never change the supplied statistics.</p>
      </div>
      <form className="investigation-form" onSubmit={startInvestigation}>
        <div className="field">
          <span>What kind of place?</span>
          <DropdownMenu
            label="What kind of place?"
            value={placeType}
            options={placeChoices.map(([id, label]) => ({ value: id, label }))}
            onChange={setPlaceType}
          />
        </div>
        <div className="field">
          <span>What do you care about?</span>
          <DropdownMenu
            label="What do you care about?"
            value={variableId}
            options={variableGlossary.map((item) => ({ value: item.variableId, label: item.name }))}
            onChange={setVariableId}
          />
        </div>
        <div className="field">
          <span>Which period?</span>
          <DropdownMenu
            label="Which period?"
            value={period}
            options={periodChoices.map(([id, label]) => ({ value: id, label }))}
            onChange={setPeriod}
          />
        </div>
        <button className="button button-primary" type="submit">Follow the trail</button>
      </form>
    </section>
  )
}

export default InvestigationStart
