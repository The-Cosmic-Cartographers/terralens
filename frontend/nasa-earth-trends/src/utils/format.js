// Number formatting for results. The files carry full-precision values; the screen
// shows what the method text promises: slopes to two decimals, p-values to three
// significant digits (scientific notation when very small).

export function formatNumber(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return Number(value).toFixed(digits)
}

export function formatSigned(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const number = Number(value)
  return `${number > 0 ? '+' : ''}${number.toFixed(digits)}`
}

export function formatP(value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const number = Number(value)
  if (number === 0) return '< 1 × 10⁻³⁰⁰'
  if (number >= 0.001) return number.toPrecision(3).replace(/0+$/, '').replace(/\.$/, '')
  const [mantissa, exponent] = number.toExponential(1).split('e')
  const power = String(Math.abs(Number(exponent)))
    .split('')
    .map((digit) => '⁰¹²³⁴⁵⁶⁷⁸⁹'[digit])
    .join('')
  return `${mantissa} × 10⁻${power}`
}

// Interval end points are stored per year; the screen shows per decade.
export function formatIntervalPerDecade(interval, digits = 2) {
  if (!Array.isArray(interval) || interval.length !== 2) return '—'
  return interval.map((value) => formatSigned(Number(value) * 10, digits)).join(' to ')
}

// Per-year slopes can be tiny (soil moisture is about 1e-4 m3/m3 per year), so a fixed
// three decimals prints "+0.000". Keep two significant figures, never fewer than three
// decimals; `reference` lets a confidence interval share its slope's precision.
export function formatSlope(value, reference = value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const size = Math.abs(Number(reference))
  const digits = size > 0 && Number.isFinite(size)
    ? Math.min(8, Math.max(3, 1 - Math.floor(Math.log10(size))))
    : 3
  return formatSigned(value, digits)
}

// Chart values: four significant figures, not the float the file stores.
export function formatChartValue(value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return String(Number(Number(value).toPrecision(4)))
}

const verdictLabels = {
  significant: 'Significant',
  weak_evidence: 'Weak evidence',
  no_clear_trend: 'No clear trend',
  not_enough_data: 'Not enough data',
}

export function verdictLabel(verdict) {
  return verdictLabels[verdict] || verdict || 'Not supplied'
}

const methodLabels = {
  'seasonal_mann_kendall_hamed_rao + sens_slope':
    'Seasonal Mann–Kendall (Hamed–Rao corrected) with Sen’s slope',
}

export function methodLabel(method) {
  return methodLabels[method] || method || 'Supplied by analysis'
}
