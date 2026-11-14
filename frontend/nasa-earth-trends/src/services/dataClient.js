const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const STATIC_DATA_BASE_URL = import.meta.env.VITE_STATIC_DATA_BASE_URL || '/data'
const DATA_MODE = import.meta.env.VITE_DATA_MODE || 'static'

const resources = {
  health: { api: '/health', static: 'health.json' },
  catalogue: { api: '/api/v1/catalogue', static: 'catalogue.json' },
  regions: { api: '/api/v1/regions', static: 'regions.json' },
  metadata: {
    api: '/api/v1/metadata',
    static: 'metadata/{datasetId}.json',
  },
  lineup: {
    api: '/api/v1/regions/{regionId}/lineup',
    static: 'lineup/{regionId}.json',
    fallback: 'results/lineup/{regionId}.json',
  },
  series: {
    api: '/api/v1/regions/{regionId}/series',
    static: 'series/{datasetId}/{regionId}.json',
  },
  trend: {
    api: '/api/v1/regions/{regionId}/trend',
    static: 'trend/{datasetId}/{regionId}.json',
    fallback: 'results/{datasetId}/trends.json',
  },
  windows: {
    api: '/api/v1/regions/{regionId}/windows',
    static: 'windows/{datasetId}/{regionId}.json',
    fallback: 'results/windows/{datasetId}/{regionId}.json',
  },
  compare: { api: '/api/v1/compare', static: 'compare/{datasetId}.json' },
}

function resolvePath(kind, params) {
  const resource = resources[kind]
  const template = DATA_MODE === 'live' ? resource.api : resource.static

  return template.replace(/\{(\w+)\}/g, (_, key) => {
    if (!params[key]) {
      throw new Error(`Missing ${key} for ${kind} request`)
    }

    return encodeURIComponent(params[key])
  })
}

function baseUrl() {
  if (DATA_MODE === 'live') return API_BASE_URL

  return STATIC_DATA_BASE_URL.startsWith('http')
    ? STATIC_DATA_BASE_URL
    : new URL(STATIC_DATA_BASE_URL, window.location.origin).toString()
}

async function request(kind, params = {}) {
  const resource = resources[kind]
  const paths = [resolvePath(kind, params)]

  if (DATA_MODE === 'static' && resource.fallback) {
    paths.push(resource.fallback.replace(/\{(\w+)\}/g, (_, key) => (
      encodeURIComponent(params[key])
    )))
  }

  let response
  let lastUrl

  for (const path of paths) {
    const url = new URL(path, `${baseUrl().replace(/\/$/, '')}/`)

    if (DATA_MODE === 'live') {
      if (params.datasetId) url.searchParams.set('dataset_id', params.datasetId)
    }

    lastUrl = url
    response = await fetch(url)

    if (response.ok) {
      const payload = await response.json()

      if ((kind === 'trend' || kind === 'lineup') && Array.isArray(payload)) {
        const result = kind === 'trend'
          ? payload.find((item) => item.region_id === params.regionId)
          : payload.find((item) => item.region_id === params.regionId)

        if (!result) throw new Error(`No ${kind} found for ${params.regionId}`)
        return result
      }

      return payload
    }
  }

  throw new Error(`Request failed (${response?.status || 'unknown'}) for ${lastUrl}`)
}

export const dataClient = {
  mode: DATA_MODE,
  health: () => request('health'),
  catalogue: () => request('catalogue'),
  regions: () => request('regions'),
  metadata: ({ datasetId }) => request('metadata', { datasetId }),
  lineup: ({ regionId }) => request('lineup', { regionId }),
  series: ({ regionId, datasetId }) => request('series', { regionId, datasetId }),
  trend: ({ regionId, datasetId }) => request('trend', { regionId, datasetId }),
  windows: ({ regionId, datasetId }) => request('windows', { regionId, datasetId }),
  compare: ({ datasetId }) => request('compare', { datasetId }),
}
