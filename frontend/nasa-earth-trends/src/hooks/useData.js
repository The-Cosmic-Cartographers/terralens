import { useEffect, useState } from 'react'

import { dataClient } from '../services/dataClient.js'

export function useData(resource, params = {}) {
  const [state, setState] = useState(() => {
    const cached = dataClient.peek(resource, params)

    return cached === undefined
      ? { data: null, loading: true, error: null }
      : { data: cached, loading: false, error: null }
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

    // A visited page renders from the cache without a loading state at all.
    const cached = dataClient.peek(resource, requestParams)
    if (cached !== undefined) {
      Promise.resolve().then(() => {
        if (active) setState({ data: cached, loading: false, error: null })
      })

      return () => {
        active = false
      }
    }

    Promise.resolve().then(() => {
      if (active) setState({ data: null, loading: true, error: null })
    })

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
