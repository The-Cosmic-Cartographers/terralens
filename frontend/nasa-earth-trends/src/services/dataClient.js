const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const STATIC_DATA_BASE_URL =
  import.meta.env.VITE_STATIC_DATA_BASE_URL || '/data/fixtures'
const DATA_MODE = import.meta.env.VITE_DATA_MODE || 'static'

const resources = {
  health: {
    api: '/health',
    static: 'health.json',
  },
  catalogue: {
    api: '/api/v1/catalogue',
    static: 'catalogue.json',
  },
  regions: {
    api: '/api/v1/regions',
    static: 'regions.json',
  },
  metadata: {
    api: '/api/v1/metadata',
    static: 'metadata/{datasetId}.json',
  },
}

function resolvePath(kind, params = {}) {
  const resource = resources[kind]

  if (!resource) {
    throw new Error(`Unsupported data resource: ${kind}`)
  }

  return resource[DATA_MODE].replace(
    '{datasetId}',
    encodeURIComponent(params.datasetId || ''),
  )
}

async function request(kind, params = {}) {
  const base = DATA_MODE === 'live' ? API_BASE_URL : STATIC_DATA_BASE_URL
  const path = resolvePath(kind, params)
  const absoluteBase = base.startsWith('http')
    ? base
    : new URL(base, window.location.origin).toString()
  const url = new URL(path, `${absoluteBase.replace(/\/$/, '')}/`)

  if (DATA_MODE === 'live' && kind === 'metadata' && params.datasetId) {
    url.searchParams.set('dataset_id', params.datasetId)
  }

  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${kind}`)
  }

  return response.json()
}

export const dataClient = {
  mode: DATA_MODE,
  health: () => request('health'),
  catalogue: () => request('catalogue'),
  regions: () => request('regions'),
  metadata: (datasetId) => request('metadata', { datasetId }),
}
