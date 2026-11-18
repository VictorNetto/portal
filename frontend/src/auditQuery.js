// The audit page's filter bar: the Hub's grammar (filterQuery.js: tokens, quotes, "-" negation,
// periods), with the audit log's own keys. The log is paginated on the server, so the query is
// turned into tokens here and filtered there (POST /audit-logs/search); dates are sent as UTC
// instants of the browser's local periods, like the Hub's.
//
// Keys:
//   action:<a>[,<b>…]   one of these actions (AUDIT_ACTIONS)
//   actor:<text>        who did it: login, display or full name, api:<prefix> or the key's label, system
//   entity:<t>[,<t>…]   the kind of record (vulnerability, report, user…); entity:none = no record
//   record:<id>         one record: VULN-0001 / the report's id, or a uuid (also its attachments)
//   date:<when>         when it happened (parsePeriod: 7d, 10-2026, 01-09-2026..30-09-2026, ..2025)
//   role:<r>[,<r>…]     the actor's role                                  (advanced)
//   ip:<text>           the IP address contains                            (advanced)
//   detail:<text>       the detail contains (field names and values)       (advanced)
//   <bare text>         anywhere: actor, action, record kind or id, detail, IP
import { tokenize, parsePeriod, DATE_VALUES } from './filterQuery'

export const AUDIT_ACTIONS = [
  'login', 'login_failed', 'logout', 'create', 'read', 'update', 'delete', 'status_change',
  'export', 'send', 'api_key_create', 'api_key_revoke', 'permission_change',
  'lock_override', 'correction', 'accept',
]
export const AUDIT_ROLES = ['admin', 'write_all', 'read_all', 'write_restricted', 'read_restricted', 'auditor', 'defense', 'dashboard']

export const AUDIT_FILTER_KEYS = [
  { key: 'action', enumerable: true, values: AUDIT_ACTIONS },
  { key: 'actor', enumerable: true, values: [] },          // from /audit-logs/facets
  { key: 'entity', enumerable: true, values: [] },         // from /audit-logs/facets
  { key: 'record', enumerable: false, values: [] },
  { key: 'date', enumerable: true, values: DATE_VALUES },
  { key: 'role', enumerable: true, values: AUDIT_ROLES, advanced: true },
  { key: 'ip', enumerable: false, values: [], advanced: true },
  { key: 'detail', enumerable: false, values: [], advanced: true },
]

const LIST_KEYS = { action: new Set(AUDIT_ACTIONS), role: new Set(AUDIT_ROLES), entity: null }
const TEXT_KEYS = new Set(['actor', 'record', 'ip', 'detail'])
const unquote = (v) => v.replaceAll('"', '')

/** One token as { raw, filter } (filter: what the server takes) or { raw, error: true }. */
function makeToken(raw) {
  let negate = false
  let body = raw
  if (body.startsWith('-') && body.length > 1) { negate = true; body = body.slice(1) }
  const colon = body.indexOf(':')
  const quote = body.indexOf('"')
  if (colon === -1 || (quote !== -1 && quote < colon)) {
    const text = unquote(body).trim()
    return text ? { raw, filter: { key: 'text', negate, text } } : { raw, error: true }
  }
  const key = body.slice(0, colon).toLowerCase()
  const value = unquote(body.slice(colon + 1)).trim()
  if (key in LIST_KEYS) {
    const values = value.split(',').map((v) => v.trim().toLowerCase()).filter(Boolean)
    const known = LIST_KEYS[key]
    if (!values.length || (known && !values.every((v) => known.has(v)))) return { raw, error: true }
    return { raw, filter: { key, negate, values } }
  }
  if (TEXT_KEYS.has(key)) return value ? { raw, filter: { key, negate, text: value } } : { raw, error: true }
  if (key === 'date') {
    const p = parsePeriod(value)
    if (!p) return { raw, error: true }
    const f = { key, negate }
    if (p.from) f.from = p.from.toISOString()
    if (p.to) f.to = p.to.toISOString()
    return { raw, filter: f }
  }
  return { raw, error: true }
}

/** The query as the server's filters, plus the tokens that can't be used (ignored, and shown). */
export function parseAuditQuery(text) {
  const tokens = tokenize(text).map(makeToken)
  return {
    filters: tokens.filter((t) => t.filter).map((t) => t.filter),
    invalid: tokens.filter((t) => t.error).map((t) => t.raw),
  }
}
