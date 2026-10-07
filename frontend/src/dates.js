// Date helpers. The API sends timestamps as UTC without a timezone marker
// (e.g. "2026-10-07T13:40:10.35"); `new Date()` would read that as *local*
// time and show it hours off. Treat markerless values as UTC.
import { locale } from './i18n'

export function parseUtc(iso) {
  if (!iso) return null
  const hasZone = /(z|[+-]\d\d:?\d\d)$/i.test(iso)
  const d = new Date(hasZone ? iso : `${iso}Z`)
  return Number.isNaN(d.getTime()) ? null : d
}

const tag = () => (locale.value === 'en' ? 'en-GB' : 'pt-BR')

export function fmtDate(iso) {
  const d = parseUtc(iso)
  return d ? d.toLocaleDateString(tag()) : '—'
}

export function fmtTime(iso) {
  const d = parseUtc(iso)
  return d ? d.toLocaleTimeString(tag(), { hour: '2-digit', minute: '2-digit' }) : ''
}

export function fmtDateTime(iso) {
  const d = parseUtc(iso)
  return d ? d.toLocaleString(tag()) : '—'
}

// "YYYY-MM-DD" (a calendar date, no time zone): format without shifting the day.
export function fmtPlainDate(value) {
  if (!value) return '—'
  const [y, m, day] = String(value).slice(0, 10).split('-').map(Number)
  if (!y || !m || !day) return '—'
  return new Date(y, m - 1, day).toLocaleDateString(tag())
}
