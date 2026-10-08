// Mirrors the server's record-level rules (backend/app/access.py, D10) so the UI offers only
// what will work. The server enforces them regardless.
const WRITES_ALL = ['admin', 'write_all']

export const writesAll = (user) => WRITES_ALL.includes(user?.role)
export const canCreate = (user) => writesAll(user) || user?.role === 'write_restricted'

const involved = (user, rec) =>
  !!rec && (rec.created_by === user.id || (rec.operators || []).some((o) => o.id === user.id))

// `parent` is the report a vulnerability belongs to, when it has one.
export function canWriteRecord(user, rec, parent = null) {
  if (writesAll(user)) return true
  if (user?.role !== 'write_restricted') return false
  return involved(user, rec) || involved(user, parent)
}

export function canDeleteRecord(user, rec, parent = null) {
  if (writesAll(user)) return true
  if (user?.role !== 'write_restricted') return false
  return rec.created_by === user.id || involved(user, parent)
}
