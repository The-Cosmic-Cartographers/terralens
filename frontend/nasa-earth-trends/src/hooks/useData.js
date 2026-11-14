import { useEffect, useState } from 'react'

import { dataClient } from '../services/dataClient.js'

export function useData(resource, params) {
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  })
  const paramsKey = JSON.stringify(params || {})

  useEffect(() => {
    let active = true
    const loader = dataClient[resource]

    if (!loader) {
      Promise.resolve().then(() => {
        if (active) {
          setState({
            data: null,
            loading: false,
            error: new Error(`Unknown data resource: ${resource}`),
          })
        }
      })

      return () => {
        active = false
      }
    }

    loader(params)
      .then((data) => {
        if (active) {
          setState({ data, loading: false, error: null })
        }
      })
      .catch((error) => {
        if (active) {
          setState({ data: null, loading: false, error })
        }
      })

    return () => {
      active = false
    }
  }, [resource, paramsKey, params])

  return {
    ...state,
    mode: dataClient.mode,
  }
}
