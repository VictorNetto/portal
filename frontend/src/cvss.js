// CVSS v3.1 base score (FIRST specification, section 7 and appendix A).
// Only the base metrics: they are what a finding's score is (temporal and environmental
// metrics depend on the moment and on each environment).

// Metrics in vector order, each with its values in the order FIRST's calculator shows them.
export const METRICS = [
  { key: 'AV', values: ['N', 'A', 'L', 'P'] },
  { key: 'AC', values: ['L', 'H'] },
  { key: 'PR', values: ['N', 'L', 'H'] },
  { key: 'UI', values: ['N', 'R'] },
  { key: 'S', values: ['U', 'C'] },
  { key: 'C', values: ['N', 'L', 'H'] },
  { key: 'I', values: ['N', 'L', 'H'] },
  { key: 'A', values: ['N', 'L', 'H'] },
]

const W = {
  AV: { N: 0.85, A: 0.62, L: 0.55, P: 0.2 },
  AC: { L: 0.77, H: 0.44 },
  PR: { U: { N: 0.85, L: 0.62, H: 0.27 }, C: { N: 0.85, L: 0.68, H: 0.5 } },  // depends on the scope
  UI: { N: 0.85, R: 0.62 },
  CIA: { H: 0.56, L: 0.22, N: 0 },
}

// "Round up" as the 3.1 specification defines it (Appendix A), immune to float noise:
// the smallest number with one decimal that is >= the input.
export function roundUp(x) {
  const i = Math.round(x * 100000)
  return i % 10000 === 0 ? i / 100000 : (Math.floor(i / 10000) + 1) / 10
}

const complete = (m) => METRICS.every(({ key, values }) => values.includes(m[key]))

/** Base score 0.0–10.0, or null while a metric is missing. */
export function baseScore(m) {
  if (!complete(m)) return null
  const iss = 1 - (1 - W.CIA[m.C]) * (1 - W.CIA[m.I]) * (1 - W.CIA[m.A])
  const impact = m.S === 'U' ? 6.42 * iss : 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
  const exploitability = 8.22 * W.AV[m.AV] * W.AC[m.AC] * W.PR[m.S][m.PR] * W.UI[m.UI]
  if (impact <= 0) return 0
  return m.S === 'U'
    ? roundUp(Math.min(impact + exploitability, 10))
    : roundUp(Math.min(1.08 * (impact + exploitability), 10))
}

/** Qualitative rating key: none, low, medium, high, critical. */
export function severity(score) {
  if (score == null) return null
  if (score === 0) return 'none'
  if (score < 4) return 'low'
  if (score < 7) return 'medium'
  if (score < 9) return 'high'
  return 'critical'
}

/** "CVSS:3.1/AV:N/…" with the metrics chosen so far (all eight once complete). */
export function toVector(m) {
  const parts = METRICS.filter(({ key }) => m[key]).map(({ key }) => `${key}:${m[key]}`)
  return parts.length ? ['CVSS:3.1', ...parts].join('/') : ''
}

/** The base metrics found in a vector string (3.0 or 3.1, prefix optional); unknown parts are ignored. */
export function parseVector(text) {
  const m = {}
  for (const part of String(text || '').split('/')) {
    const [key, value] = part.trim().split(':')
    const metric = METRICS.find((x) => x.key === key)
    if (metric && metric.values.includes(value)) m[key] = value
  }
  return m
}
