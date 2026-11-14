export const variableGlossary = [
  {
    variableId: 't2m',
    datasetId: 'merra2_m2tmnxslv',
    name: 'Air temperature',
    unit: '°C',
    source: 'MERRA-2 model reanalysis',
    definition: 'How warm the air is at about head height.',
    whyItMatters: 'A baseline heat signal linked to seasonal conditions and water demand.',
  },
  {
    variableId: 'soil_moisture_0_10',
    datasetId: 'gldas_noah025_m21_soilmoi0_10',
    name: 'Soil moisture',
    unit: 'kg/m²',
    source: 'GLDAS land model',
    definition: 'How wet the top 10 centimetres of soil are.',
    whyItMatters: 'Connects rainfall with plants, evaporation and drought conditions.',
  },
  {
    variableId: 'precipitation',
    datasetId: 'gpm_3imergm_v07b',
    name: 'Precipitation',
    unit: 'mm/month',
    source: 'GPM IMERG satellite estimate',
    definition: 'Rain and snow reaching the ground during a month.',
    whyItMatters: 'Describes water arriving at the surface and the balance between wet and dry seasons.',
  },
  {
    variableId: 'evapotranspiration',
    datasetId: 'gldas_noah025_m21_evap',
    name: 'Evapotranspiration',
    unit: 'mm/day',
    source: 'GLDAS land model',
    definition: 'Water returned to the air by soil and plants.',
    whyItMatters: 'Shows how heat, vegetation and available water interact.',
  },
  {
    variableId: 'aerosol',
    datasetId: 'merra2_m2tmnxaer_v5_12_4',
    name: 'Aerosol optical depth',
    unit: 'unitless',
    source: 'MERRA-2 model reanalysis',
    definition: 'How much airborne particle haze blocks or scatters light.',
    whyItMatters: 'Helps describe dust, smoke and pollution in the atmospheric column.',
  },
]

export const verdictGlossary = [
  ['significant', 'Significant trend', 'Adjusted p-value is below 0.05.'],
  ['weak_evidence', 'Weak evidence', 'Adjusted p-value is between 0.05 and 0.10.'],
  ['no_clear_trend', 'No clear trend', 'The supplied test cannot separate a trend from noise.'],
  ['not_enough_data', 'Not enough data', 'Coverage or record length is below the analysis threshold.'],
]
