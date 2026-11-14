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
  {
    key: 'significant',
    label: 'Significant trend',
    rule: 'Adjusted p < 0.05',
    explanation: 'Fewer than 5 in 100: if nothing were changing, a result this strong would appear in fewer than five out of a hundred records like this one. The direction is unlikely to be noise. It does not mean the change is large, fast, or caused by anything in particular.',
  },
  {
    key: 'weak_evidence',
    label: 'Weak evidence',
    rule: 'Adjusted p 0.05–0.10',
    explanation: 'Between 5 and 10 in 100: a result this strong would appear in five to ten out of a hundred records with no trend. That is suggestive, not a claim, and the confidence interval usually still includes a flat line.',
  },
  {
    key: 'no_clear_trend',
    label: 'No clear trend',
    rule: 'Adjusted p ≥ 0.10',
    explanation: 'More than 10 in 100: a result this strong would appear in more than ten out of a hundred records with no trend. The test cannot separate a trend from noise over this record. It is not evidence that the value is unchanged — a slow trend hidden by year-to-year swings looks exactly the same.',
  },
  {
    key: 'not_enough_data',
    label: 'Not enough data',
    rule: 'Test not run',
    explanation: 'Too few usable months to test: fewer than ten complete years, or months missing or below the 50% coverage gate. A p-value from a shorter record would overstate confidence, so none is reported.',
  },
]
