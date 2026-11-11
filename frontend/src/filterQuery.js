// Single-line filter grammar for the Hub list.
//
// Space-separated tokens, ANDed. Each token may be negated with a leading "-".
//   key:value        include rows matching
//   -key:value       exclude rows matching
//   <bare text>      free search on identifier (negatable: -text)
// A value is only what follows the ":" up to the next space. To include spaces, quote it:
//   report:"Rede do Data Center"   "texto com espaços"   -"sem rotação"
//
// Keys:
//   status:<one of STATUSES>     exact status
//   cvss:<x>                     CVSS >= x  (x: 0..10, at most 1 decimal)
//   operator:<text>              an operator's username contains (ci)
//   source:<text>                source contains (ci)
//   report:<text>                report id or name contains (ci); report:none = not in a report
//   <date key>:<when>            the row's date for that key falls in <when> (DATE_KEYS;
//                                see parsePeriod): 7d, 3m, 1y, or d1.d2.d3 (dd-mm-aaaa, mm-aaaa, aaaa).
//     A row without that date never matches, so -sent:15d also keeps the unsent ones.
//
// The "/" menu lists only the basic keys, plus "more filters" for the advanced ones
// (`advanced: true`). Typing a key's name finds it either way.
import { parseUtc } from './dates'

export const STATUSES = [
  'draft', 'ready', 'sent', 'fixing', 'retesting', 'fixed', 'risk_accepted',
]

// CVSS menu values: whole numbers 10..1 (reverse order). cvss:x means >= x.
export const CVSS_VALUES = ['10', '9', '8', '7', '6', '5', '4', '3', '2', '1']

// Date keys and the row field each one reads.
export const DATE_KEYS = {
  created: 'created_at',
  updated: 'updated_at',
  sent: 'sent_at',
  accepted: 'accepted_at',
  fixing: 'fixing_at',
  retesting: 'retesting_at',
  fixed: 'fixed_at',
  risk: 'risk_accepted_at',
}
// Suggested values in a date key's menu.
export const DATE_VALUES = ['1d', '7d', '30d', '90d', '1y']
const dateKey = (key) => ({ key, enumerable: true, values: DATE_VALUES, advanced: true })

// `enumerable: true` means the key has a known, listable value set and should
// show a second value menu after selection (SecTools style). `values` may be
// static (status, cvss) or resolved dynamically (operator — from loaded rows).
// `advanced: true` keeps a key out of the first "/" menu (behind "more filters").
export const FILTER_KEYS = [
  { key: 'status', enumerable: true, values: STATUSES },
  { key: 'cvss', enumerable: true, values: CVSS_VALUES },
  { key: 'report', enumerable: false, values: [] },
  { key: 'operator', enumerable: true, values: [] },
  { key: 'source', enumerable: false, values: [], advanced: true },
  ...Object.keys(DATE_KEYS).map(dateKey),
]

// The defense team's list (D17): only released statuses and their dates; no operator or source.
export const DEFENSE_FILTER_KEYS = [
  { key: 'status', enumerable: true, values: ['sent', 'fixing', 'retesting', 'fixed', 'risk_accepted'] },
  { key: 'cvss', enumerable: true, values: CVSS_VALUES },
  { key: 'report', enumerable: false, values: [] },
  ...['sent', 'accepted', 'fixing', 'retesting', 'fixed', 'risk'].map(dateKey),
]

// --- dates ------------------------------------------------------------------
// All periods are in the browser's local time, like the dates the lists show.
//
// Relative: 7d, 3m, 2y = the last 7 days (today included; 1d = today), 3 months, 2 years.
// Explicit: up to three dates separated by dots, d1.d2.d3, each dd-mm-aaaa, mm-aaaa or aaaa
// (one-digit days and months are fine):
//   d1..d3    from the start of d1 to the end of d3
//   d1..      d1 or later
//   ..d3      d3 or earlier
//   .d2.      within d2 (that day, month or year); a single date without dots means the same
//   d2 counts only on its own: with d1 or d3 present, it is ignored.
const DAY_RE = /^(\d{1,2})-(\d{1,2})-(\d{4})$/
const MONTH_RE = /^(\d{1,2})-(\d{4})$/
const YEAR_RE = /^(\d{4})$/

// One day, month or year as [start, end) local times; null when not a real date.
function calendarSpan(text) {
  let m = DAY_RE.exec(text)
  if (m) {
    const [d, mo, y] = [Number(m[1]), Number(m[2]) - 1, Number(m[3])]
    const start = new Date(y, mo, d)
    if (start.getFullYear() !== y || start.getMonth() !== mo || start.getDate() !== d) return null
    return [start, new Date(y, mo, d + 1)]
  }
  m = MONTH_RE.exec(text)
  if (m) {
    const [mo, y] = [Number(m[1]) - 1, Number(m[2])]
    if (mo < 0 || mo > 11) return null
    return [new Date(y, mo, 1), new Date(y, mo + 1, 1)]
  }
  m = YEAR_RE.exec(text)
  if (m) {
    const y = Number(m[1])
    return [new Date(y, 0, 1), new Date(y + 1, 0, 1)]
  }
  return null
}

/** A date filter's value as { from, to } (local Dates, either may be null; `to` exclusive); null if invalid. */
export function parsePeriod(text, now = new Date()) {
  const v = String(text || '').trim().toLowerCase()
  const [y, mo, d] = [now.getFullYear(), now.getMonth(), now.getDate()]
  const rel = /^(\d{1,4})([dmy])$/.exec(v)
  if (rel) {
    const n = Number(rel[1])
    if (n < 1) return null
    if (rel[2] === 'd') return { from: new Date(y, mo, d - (n - 1)), to: null }
    if (rel[2] === 'm') return { from: new Date(y, mo - n, d), to: null }
    return { from: new Date(y - n, mo, d), to: null }
  }

  const parts = v.split('.')
  if (parts.length === 1) parts.splice(0, 1, '', parts[0], '')    // a single date is d2
  if (parts.length !== 3) return null
  const [d1, d2, d3] = parts.map((p) => (p ? calendarSpan(p) : undefined))
  if ([d1, d2, d3].includes(null)) return null                     // a date that doesn't exist
  if (d1 || d3) {
    if (d1 && d3 && d3[1] <= d1[0]) return null                    // the range ends before it starts
    return { from: d1 ? d1[0] : null, to: d3 ? d3[1] : null }
  }
  return d2 ? { from: d2[0], to: d2[1] } : null
}

// CVSS value: 0..10 with at most one decimal place. Accepts "7", "7.8", "10".
// Rejects "5.77", "-1", "10.1", "11", "".
const CVSS_RE = /^(?:10(?:\.0)?|[0-9](?:\.[0-9])?)$/
export function isValidCvss(v) {
  return CVSS_RE.test(v)
}

const STATUS_SET = new Set(STATUSES)

// Splits on spaces, except inside double quotes. An unclosed quote runs to the end.
export function tokenize(text) {
  const s = text || ''
  const out = []
  let i = 0
  while (i < s.length) {
    while (i < s.length && /\s/.test(s[i])) i++
    let raw = ''
    while (i < s.length && !/\s/.test(s[i])) {
      if (s[i] === '"') {
        const end = s.indexOf('"', i + 1)
        const stop = end === -1 ? s.length : end + 1
        raw += s.slice(i, stop)
        i = stop
      } else raw += s[i++]
    }
    if (raw) out.push(raw)
  }
  return out
}

const unquote = (v) => v.replaceAll('"', '')

function makeToken(raw) {
  let negate = false
  let body = raw
  if (body.startsWith('-') && body.length > 1) {
    negate = true
    body = body.slice(1)
  }

  // A ":" inside quotes is text, not a key.
  const colon = body.indexOf(':')
  const quote = body.indexOf('"')
  if (colon === -1 || (quote !== -1 && quote < colon)) {
    const value = unquote(body)
    return { raw, negate, key: 'text', op: 'contains', value, valid: value.length > 0 }
  }
  const key = body.slice(0, colon).toLowerCase()
  const value = unquote(body.slice(colon + 1))

  if (key === 'status')
    return { raw, negate, key, op: '=', value, valid: STATUS_SET.has(value) }
  if (key === 'cvss')
    return { raw, negate, key, op: '>=', value: Number(value), valid: isValidCvss(value) }
  if (key === 'source' || key === 'operator' || key === 'report')
    return { raw, negate, key, op: 'contains', value, valid: value.length > 0 }
  if (key in DATE_KEYS) {
    const period = parsePeriod(value)
    return { raw, negate, key, op: 'in', value: period, valid: period !== null }
  }
  return { raw, negate, key, op: '?', value, valid: false }
}

function baseMatch(tok, r) {
  switch (tok.key) {
    case 'status':
      return r.status === tok.value
    case 'text':
      return (r.identifier || '').toLowerCase().includes(tok.value.toLowerCase())
    case 'source':
      return (r.source || '').toLowerCase().includes(tok.value.toLowerCase())
    case 'report': {
      if (tok.value.toLowerCase() === 'none') return !r.report
      const text = r.report ? `${r.report.internal_id || ''} ${r.report.name || ''}`.toLowerCase() : ''
      return text.includes(tok.value.toLowerCase())
    }
    case 'operator': {
      const ops = Array.isArray(r.operators) ? r.operators : []
      const q = tok.value.toLowerCase()
      // operators may be objects {username} or plain strings
      return ops.some((o) => {
        const name = typeof o === 'string' ? o : (o?.username || '')
        return name.toLowerCase().includes(q)
      })
    }
    case 'cvss':
      return r.cvss_score !== null && r.cvss_score !== undefined &&
        Number(r.cvss_score) >= tok.value
    default: {
      if (!(tok.key in DATE_KEYS)) return true
      const d = parseUtc(r[DATE_KEYS[tok.key]])
      return !!d && (!tok.value.from || d >= tok.value.from) && (!tok.value.to || d < tok.value.to)
    }
  }
}

function tokenPredicate(tok) {
  if (!tok.valid) return () => true // ignore invalid tokens rather than hide all
  return (r) => {
    const m = baseMatch(tok, r)
    return tok.negate ? !m : m
  }
}

export function parseQuery(text) {
  const tokens = tokenize(text).map(makeToken)
  const preds = tokens.map(tokenPredicate)
  return { tokens, predicate: (row) => preds.every((p) => p(row)) }
}
