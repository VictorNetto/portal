// How a person is named in the UI: the display name, else the full name, else the login.
// Works on any user shape: OperatorRef ({name}), /users rows ({display_name, full_name}),
// or a plain string.
export function userName(u) {
  if (!u) return ''
  if (typeof u === 'string') return u
  return u.name || u.display_name || u.full_name || u.username || ''
}

// Does a search text match the person (by any of their names or their login)?
export function userMatches(u, needle) {
  if (!needle) return true
  const q = needle.toLowerCase()
  if (typeof u === 'string') return u.toLowerCase().includes(q)
  return [u.name, u.display_name, u.full_name, u.username].some((s) => s && s.toLowerCase().includes(q))
}
