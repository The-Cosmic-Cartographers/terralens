import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
        <span className="section-index">START AN INVESTIGATION</span>
        <h2 id="start-investigation-title">Ask a smaller question. See the evidence faster.</h2>
        <p>Choose the kind of place, the signal you care about, and the period you want to inspect. These choices filter the Lineup; they never change the supplied statistics.</p>
      </div>
      <form className="investigation-form" onSubmit={startInvestigation}>
        <label>
          <span>What kind of place?</span>
          <select value={placeType} onChange={(event) => setPlaceType(event.target.value)}>
            {placeChoices.map(([id, label]) => <option value={id} key={id}>{label}</option>)}
          </select>
        </label>
        <label>
          <span>What do you care about?</span>
          <select value={variableId} onChange={(event) => setVariableId(event.target.value)}>
            {variableGlossary.map((item) => <option value={item.variableId} key={item.variableId}>{item.name}</option>)}
          </select>
        </label>
        <label>
          <span>Which period?</span>
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            {periodChoices.map(([id, label]) => <option value={id} key={id}>{label}</option>)}
          </select>
        </label>
        <button className="button button-primary" type="submit">Follow the trail</button>
      </form>
    </section>
  )
}

export default InvestigationStart
