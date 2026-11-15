import { useEffect, useMemo, useState } from 'react'

import { dataClient } from '../services/dataClient.js'
import { useWindow } from '../state/window.js'
import { neededWindows, windowedLineup } from '../utils/windows.js'

// The lineups the page loaded, re-read for the header's window. `lineups` is a list
// of lineup objects (undefined while loading). `pending` is true while the windows
// files for a window shorter than the record are still on the network.
export function useWindowedLineups(lineups) {
  const { startYear, endYear } = useWindow()
  const [loaded, setLoaded] = useState({})

  const needed = useMemo(
    () => neededWindows(lineups.filter(Boolean), startYear, endYear),
    [lineups, startYear, endYear],
  )
  const neededKey = needed.map((item) => `${item.regionId}|${item.datasetId}`).join(',')

  useEffect(() => {
    let active = true

    needed.forEach(({ regionId, datasetId }) => {
      const key = `${regionId}|${datasetId}`
      if (dataClient.peek('windows', { regionId, datasetId }) !== undefined) return

      dataClient.windows({ regionId, datasetId })
        .then((file) => { if (active) setLoaded((current) => ({ ...current, [key]: file })) })
        .catch(() => { if (active) setLoaded((current) => ({ ...current, [key]: null })) })
    })

    return () => { active = false }
    // `needed` is derived from neededKey; the key is the stable dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [neededKey])

  const windowsByKey = useMemo(() => {
    const byKey = {}
    needed.forEach(({ regionId, datasetId }) => {
      const key = `${regionId}|${datasetId}`
      const cached = dataClient.peek('windows', { regionId, datasetId })
      byKey[key] = cached !== undefined ? cached : loaded[key]
    })
    return byKey
    // `loaded` changes when a request settles; the cache is read at that moment.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [neededKey, loaded])

  const pending = needed.some(({ regionId, datasetId }) => windowsByKey[`${regionId}|${datasetId}`] === undefined)

  const windowed = useMemo(
    () => lineups.map((lineup) => (lineup ? windowedLineup(lineup, windowsByKey, startYear, endYear) : lineup)),
    [lineups, windowsByKey, startYear, endYear],
  )

  return { lineups: windowed, pending, startYear, endYear }
}
