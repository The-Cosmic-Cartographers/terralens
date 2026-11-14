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
