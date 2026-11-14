import { useEffect, useState } from 'react'

import { dataClient } from '../services/dataClient.js'

export function useData(resource, params = {}) {
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  })
  const paramsKey = JSON.stringify(params)

  useEffect(() => {
    let active = true
    const loader = dataClient[resource]
    const requestParams = JSON.parse(paramsKey)

    if (Object.values(requestParams).some((value) => value == null || value === '')) {
      Promise.resolve().then(() => {
        if (active) setState({ data: null, loading: false, error: null })
      })

      return () => {
        active = false
      }
    }

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

    loader(requestParams)
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
  }, [resource, paramsKey])

  return {
    ...state,
    mode: dataClient.mode,
  }
}
