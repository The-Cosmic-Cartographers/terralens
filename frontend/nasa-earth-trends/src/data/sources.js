// Where each product actually lives. The UI uses these as the stable fallback
// when a provenance record carries no usable link for the region in view.
export const datasetSources = {
  merra2_m2tmnxslv: {
    label: 'MERRA-2 2 m air temperature (M2TMNXSLV)',
    url: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXSLV_5.12.4/summary',
  },
  merra2_m2tmnxaer_v5_12_4: {
    label: 'MERRA-2 aerosol diagnostics (M2TMNXAER)',
    url: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXAER_5.12.4/summary',
  },
  merra2_m2tmnxlnd_sfmc_v5_12_4: {
    label: 'MERRA-2 land surface diagnostics (M2TMNXLND)',
    url: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXLND_5.12.4/summary',
  },
  merra2_m2tmnxlnd_evland_v5_12_4: {
    label: 'MERRA-2 land surface diagnostics (M2TMNXLND)',
    url: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXLND_5.12.4/summary',
  },
  merra2_m2tmnxflx_prectotcorr_v5_12_4: {
    label: 'MERRA-2 surface flux diagnostics (M2TMNXFLX)',
    url: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXFLX_5.12.4/summary',
  },
  omi_omno2d_v004: {
    label: 'OMI tropospheric NO2 column (OMNO2D)',
    url: 'https://disc.gsfc.nasa.gov/datasets/OMNO2D_004/summary',
  },
  gldas_noah025_m21_soilmoi0_10: {
    label: 'GLDAS Noah 2.1 land surface model (GLDAS_NOAH025_M_2.1)',
    url: 'https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_M_2.1/summary',
  },
  gldas_noah025_m21_evap: {
    label: 'GLDAS Noah 2.1 land surface model (GLDAS_NOAH025_M_2.1)',
    url: 'https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_M_2.1/summary',
  },
  gpm_3imergm_v07b: {
    label: 'GPM IMERG monthly V07 (GPM_3IMERGM)',
    url: 'https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGM_07/summary',
  },
}

function httpUrl(value) {
  const text = typeof value === 'string' ? value.trim() : ''
  return /^https?:\/\//i.test(text) ? text : null
}

export function datasetSourceUrl(datasetId) {
  return datasetSources[datasetId]?.url ?? null
}

const HARMONY_JOB = /^https?:\/\/harmony\.earthdata\.nasa\.gov\/jobs\/([0-9a-f-]{8,})/i

// A Harmony job page opens only for the account that ran it, behind an Earthdata
// login, so it is a record of how a series was made and never a link to follow.
function isHarmonyJob(url) {
  return HARMONY_JOB.test(url ?? '')
}

// The link behind "Source": the product's own public page. A region's Giovanni
// permalink is the fallback, and a Harmony job page is never used.
export function provenanceUrl(provenance, regionId) {
  const region = regionId ? provenance?.regions?.[regionId] : null
  const permalink = httpUrl(region?.permalink)
  const fallback = httpUrl(provenance?.doi_or_url)

  return datasetSourceUrl(provenance?.dataset_id)
    ?? (permalink && !isHarmonyJob(permalink) ? permalink : null)
    ?? (fallback && !isHarmonyJob(fallback) ? fallback : null)
}

// How this region's series was fetched, for the evidence record: a Giovanni
// request is a link anyone can open; a Harmony job is shown as an id.
export function accessRecord(provenance, regionId) {
  const region = regionId ? provenance?.regions?.[regionId] : null
  const permalink = httpUrl(region?.permalink) ?? httpUrl(provenance?.doi_or_url)
  const route = provenance?.access_route || null

  if (!permalink) return route ? { label: route, href: null } : null

  const job = permalink.match(HARMONY_JOB)
  if (job) return { label: `${route ?? 'NASA Harmony'}, job ${job[1].slice(0, 8)}`, href: null }

  return { label: route ?? 'Giovanni request', href: permalink }
}
