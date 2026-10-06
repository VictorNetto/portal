// Slash-command filter grammar for the Hub list.
//
// Space-separated tokens, applied as AND. Supported keys:
//   status:<value>         exact status match
//   cvss:>7 cvss:>=7 cvss:<5 cvss:<=5 cvss:7   numeric comparison
//   id:<text> / identifier:<text>              identifier contains (ci)
//   source:<text>                              source contains (ci)
//   <bare text>                                free search on identifier
//
// parseQuery -> { predicate(row), tokens: [{raw, key, op, value, valid}] }

const STATUSES = new Set([
  'draft', 'saved_local', 'dispatching', 'dispatched',
  'acknowledged', 'waiting_fix', 'pending_retest', 'fixed',
])

const CVSS_RE = /^(>=|<=|>|<|=)?\s*(\d+(?:\.\d+)?)$/

function makeToken(raw) {
  const colon = raw.indexOf(':')
  if (colon === -1) {
    return { raw, key: 'id', op: 'contains', value: raw, valid: raw.length > 0 }
  }
  let key = raw.slice(0, colon).toLowerCase()
  const value = raw.slice(colon + 1)
  if (key === 'identifier') key = 'id'

  if (key === 'status') {
    return { raw, key, op: '=', value, valid: STATUSES.has(value) }
  }
  if (key === 'cvss') {
    const m = value.match(CVSS_RE)
    if (!m) return { raw, key, op: '?', value, valid: false }
    return { raw, key, op: m[1] || '=', value: Number(m[2]), valid: true }
  }
  if (key === 'id' || key === 'source') {
    return { raw, key, op: 'contains', value, valid: value.length > 0 }
  }
  return { raw, key, op: '?', value, valid: false }
}

function tokenPredicate(tok) {
  if (!tok.valid) return () => true // ignore invalid tokens rather than hide all
  switch (tok.key) {
    case 'status':
      return (r) => r.status === tok.value
    case 'id':
      return (r) => (r.identifier || '').toLowerCase().includes(tok.value.toLowerCase())
    case 'source':
      return (r) => (r.source || '').toLowerCase().includes(tok.value.toLowerCase())
    case 'cvss':
      return (r) => {
        if (r.cvss_score === null || r.cvss_score === undefined) return false
        const n = Number(r.cvss_score)
        switch (tok.op) {
          case '>': return n > tok.value
          case '>=': return n >= tok.value
          case '<': return n < tok.value
          case '<=': return n <= tok.value
          default: return n === tok.value
        }
      }
    default:
      return () => true
  }
}

export function parseQuery(text) {
  const tokens = (text || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map(makeToken)
  const preds = tokens.map(tokenPredicate)
  return {
    tokens,
    predicate: (row) => preds.every((p) => p(row)),
  }
}

export const FILTER_HELP = [
  { token: 'status:draft', desc: 'status exato' },
  { token: 'cvss:>7', desc: 'CVSS maior que' },
  { token: 'cvss:<=5', desc: 'CVSS menor ou igual' },
  { token: 'id:CVE-2024', desc: 'identificador contém' },
  { token: 'source:nuclei', desc: 'fonte contém' },
  { token: 'XSS', desc: 'busca livre no identificador' },
]
