// Dashboards (D18): labels, colors and messages for the results the API computes
// (backend/app/services/dashboard_engine.py). The language itself is in docs/specs/DASHBOARDS.md.
import { t, locale } from './i18n'

export const OTHERS = '__others__'
export const NONE = '__none__'

/** A group's or series' label: statuses and severities are translated, the rest comes named. */
export function groupLabel(dim, item) {
  const k = item?.key
  if (k === OTHERS) return t('dash.others')
  if (k === NONE) return t(`dash.none.${dim}`)
  if (dim === 'status') return t(`status.${k}`)
  if (dim === 'severity') return t(`cvssCalc.sev.${k}`)
  return item?.label ?? String(k)
}

const MONTHS = { 'pt-BR': 'pt-BR', en: 'en-US' }
/** A time bucket's label, from its start date (yyyy-mm-dd) and unit. */
export function bucketLabel(iso, unit, short = false) {
  const [y, m, d] = iso.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  const loc = MONTHS[locale.value] || 'pt-BR'
  if (unit === 'year') return String(y)
  if (unit === 'quarter') return `T${Math.floor((m - 1) / 3) + 1} ${short ? String(y).slice(2) : y}`
  if (unit === 'month') {
    const name = date.toLocaleDateString(loc, { month: 'short' }).replace('.', '')
    return short ? name : `${name} ${y}`
  }
  return date.toLocaleDateString(loc, { day: '2-digit', month: '2-digit' })
}

/** A value as shown: counts whole, durations with one decimal, missing as a dash. */
export function fmtValue(v, result) {
  if (v === null || v === undefined) return '—'
  if (result.measure === 'count') return Math.round(v).toLocaleString(locale.value)
  return Number(v).toLocaleString(locale.value, { maximumFractionDigits: 1, minimumFractionDigits: 0 })
}

/** What the number means, e.g. "Mediana de dias, sent → fixed". */
export function measureLabel(result) {
  if (result.measure === 'count') return t('dash.count')
  const agg = result.agg.startsWith('p') && result.agg.length === 3
    ? result.agg.toUpperCase() : t(`dash.agg.${result.agg}`)
  return `${agg} (${t('dash.days')}, ${result.range[0]}..${result.range[1]})`
}

// Series colors. Severity and status keep their meaning (the portal's own colors);
// other groupings take a fixed categorical order, never cycled: past 8, "Outros".
const LIGHT = {
  severity: { critical: '#9f1239', high: '#d1242f', medium: '#e08a1e', low: '#8a96a6', none: '#c3cad3' },
  status: { draft: '#b4bdc8', ready: '#0369a1', sent: '#6d3fd6', fixing: '#c26a12', retesting: '#d4a514', fixed: '#137a3d', risk_accepted: '#5f6d7e' },
  palette: ['#4f46e5', '#0891b2', '#16a34a', '#d97706', '#db2777', '#64748b', '#7c3aed', '#0d9488'],
  others: '#c3cad3', single: '#4f46e5',
}
const DARK = {
  severity: { critical: '#ff4d6d', high: '#ff8a3d', medium: '#f5c542', low: '#7d8fa6', none: '#4a5868' },
  status: { draft: '#5b6b7d', ready: '#38a3e0', sent: '#9b7bff', fixing: '#f0a14a', retesting: '#f5c542', fixed: '#3ccf7b', risk_accepted: '#8a9bb0' },
  palette: ['#8b85ff', '#38bdf8', '#4ade80', '#fbbf24', '#f472b6', '#94a3b8', '#c084fc', '#2dd4bf'],
  others: '#4a5868', single: '#8b85ff',
}

/** Color of a series (or of the bars of a single-series chart grouped by `dim`). */
export function colorOf(dim, key, index, dark = false) {
  const pal = dark ? DARK : LIGHT
  if (key === OTHERS || key === NONE) return pal.others
  if (dim === 'severity' || dim === 'status') return pal[dim][key] || pal.others
  if (index === null || index === undefined) return pal.single
  return pal.palette[index] ?? pal.others
}

/** An error from the API ({code, pos, params}) as a sentence in the user's language. */
export function errorText(e) {
  if (!e || typeof e !== 'object' || !e.code) return typeof e === 'string' ? e : t('errors.load')
  const msg = t(`dash.err.${e.code}`, e.params || {})
  return e.code === 'unavailable' || e.code === 'tv_dim' ? msg : `${msg} ${t('dash.err.position', { pos: e.pos + 1 })}`
}

// Intervals offered in the editor (seconds). Data: 30 s to 1 h; a TV screen: 5 s to 10 min.
export const REFRESH_CHOICES = [30, 60, 120, 300, 600, 900, 1800, 3600]
export const ROTATE_CHOICES = [10, 15, 20, 30, 45, 60, 120, 300]

/** 45 → "45 s", 120 → "2 min", 3600 → "1 h". */
export function fmtSeconds(n) {
  if (n < 60) return `${n} s`
  if (n < 3600) return n % 60 ? `${Math.floor(n / 60)} min ${n % 60} s` : `${n / 60} min`
  return n % 3600 ? `${Math.floor(n / 3600)} h ${Math.round((n % 3600) / 60)} min` : `${n / 3600} h`
}
