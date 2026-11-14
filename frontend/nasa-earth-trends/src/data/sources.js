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

// Prefer the link the pipeline recorded for this exact region: a Giovanni
// permalink or a Harmony job that produced the series on screen. Fall back to
// the product page, never to a link for a different region.
export function provenanceUrl(provenance, regionId) {
  const region = regionId ? provenance?.regions?.[regionId] : null
  return httpUrl(region?.permalink)
    ?? datasetSourceUrl(provenance?.dataset_id)
    ?? httpUrl(provenance?.doi_or_url)
}
