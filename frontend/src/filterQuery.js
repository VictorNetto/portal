// Single-line filter grammar for the Hub list.
//
// Space-separated tokens, ANDed. Each token may be negated with a leading "-".
//   key:value        include rows matching
//   -key:value       exclude rows matching
//   <bare text>      free search on identifier (negatable: -text)
//
// Keys:
//   status:<one of STATUSES>     exact status
//   cvss:<x>                     CVSS >= x  (x: 0..10, at most 1 decimal)
//   id:<text> / identifier:<text>  identifier contains (ci)
//   source:<text>                source contains (ci)

export const STATUSES = [
  'draft', 'saved_local', 'dispatching', 'dispatched',
  'acknowledged', 'waiting_fix', 'pending_retest', 'fixed',
]

export const FILTER_KEYS = [
  { key: 'status', desc: 'status exato', values: STATUSES },
  { key: 'cvss', desc: 'CVSS ≥ x (0–10, 1 casa decimal)', values: ['5', '7', '7.8', '9', '10'] },
  { key: 'id', desc: 'identificador contém', values: [] },
  { key: 'source', desc: 'fonte contém', values: [] },
]

// CVSS value: 0..10 with at most one decimal place. Accepts "7", "7.8", "10".
// Rejects "5.77", "-1", "10.1", "11", "".
const CVSS_RE = /^(?:10(?:\.0)?|[0-9](?:\.[0-9])?)$/
export function isValidCvss(v) {
  return CVSS_RE.test(v)
}

const STATUS_SET = new Set(STATUSES)

function makeToken(raw) {
  let negate = false
  let body = raw
  if (body.startsWith('-') && body.length > 1) {
    negate = true
    body = body.slice(1)
  }

  const colon = body.indexOf(':')
  if (colon === -1) {
    return { raw, negate, key: 'id', op: 'contains', value: body, valid: body.length > 0 }
  }
  let key = body.slice(0, colon).toLowerCase()
  const value = body.slice(colon + 1)
  if (key === 'identifier') key = 'id'

  if (key === 'status')
    return { raw, negate, key, op: '=', value, valid: STATUS_SET.has(value) }
  if (key === 'cvss')
    return { raw, negate, key, op: '>=', value: Number(value), valid: isValidCvss(value) }
  if (key === 'id' || key === 'source')
    return { raw, negate, key, op: 'contains', value, valid: value.length > 0 }
  return { raw, negate, key, op: '?', value, valid: false }
}

function baseMatch(tok, r) {
  switch (tok.key) {
    case 'status':
      return r.status === tok.value
    case 'id':
      return (r.identifier || '').toLowerCase().includes(tok.value.toLowerCase())
    case 'source':
      return (r.source || '').toLowerCase().includes(tok.value.toLowerCase())
    case 'cvss':
      return r.cvss_score !== null && r.cvss_score !== undefined &&
        Number(r.cvss_score) >= tok.value
    default:
      return true
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
  const tokens = (text || '').trim().split(/\s+/).filter(Boolean).map(makeToken)
  const preds = tokens.map(tokenPredicate)
  return { tokens, predicate: (row) => preds.every((p) => p(row)) }
}
