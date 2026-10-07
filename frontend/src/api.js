// Thin fetch wrapper for the backend API. All calls go through nginx at /api,
// so the frontend never needs to know the backend's address.

const BASE = '/api'

let accessToken = null
export function setAccessToken(token) {
  accessToken = token
}

// --- Session refresh -------------------------------------------------------
// Access tokens are short-lived (15 min). On a 401 we ask the auth store for a
// new one once (refresh tokens last days) and retry; if that fails, the session
// is over and the app is told to go back to the login page.
let refreshHandler = null
export function setRefreshHandler(fn) {
  refreshHandler = fn
}
let refreshing = null // shared so parallel 401s trigger a single refresh

async function refreshAccessToken() {
  if (!refreshHandler) return false
  refreshing ??= refreshHandler().finally(() => { refreshing = null })
  return refreshing
}

// fetch + bearer token + one transparent refresh-and-retry on 401.
async function authedFetch(url, init = {}, auth = true) {
  const send = () => fetch(url, {
    ...init,
    headers: { ...init.headers, ...(auth && accessToken ? { Authorization: `Bearer ${accessToken}` } : {}) },
  })
  let res = await send()
  if (res.status === 401 && auth && await refreshAccessToken()) res = await send()
  if (res.status === 401 && auth) window.dispatchEvent(new Event('session-expired'))
  return res
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  // FormData (file uploads) must set its own multipart Content-Type boundary.
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData
  const headers = isForm ? {} : { 'Content-Type': 'application/json' }

  const res = await authedFetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : (isForm ? body : JSON.stringify(body)),
  }, auth)

  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    // The server blocks accounts flagged must_change_password (first login, or
    // after an admin reset). Let the app react wherever the call came from.
    if (res.status === 403 && data?.detail === 'password_change_required') {
      window.dispatchEvent(new Event('password-change-required'))
    }
    throw new ApiError(res.status, data?.detail)
  }
  return data
}

// --- Vulnerability endpoints ---
export const listVulns = () => api('/vulnerabilities')
export const getVuln = (id) => api(`/vulnerabilities/${id}`)
export const createVuln = (body) => api('/vulnerabilities', { method: 'POST', body })
export const updateVuln = (id, body) =>
  api(`/vulnerabilities/${id}`, { method: 'PATCH', body })
export const sendVuln = (id) => api(`/vulnerabilities/${id}/send`, { method: 'POST' })
export const dispatchVuln = (id) => api(`/vulnerabilities/${id}/dispatch`, { method: 'POST' })
export const setVulnRvs = (id, rvsId) =>
  api(`/vulnerabilities/${id}/rvs`, { method: 'POST', body: { rvs_id: rvsId } })
export const rvsQueue = () => api('/rvs-queue')
export const deleteVuln = (id) => api(`/vulnerabilities/${id}`, { method: 'DELETE' })

// --- User management ---
export const listUsers = () => api('/users')
export const createUser = (body) => api('/users', { method: 'POST', body })
export const updateUser = (id, body) => api(`/users/${id}`, { method: 'PATCH', body })
export const resetUserPassword = (id, newPassword) =>
  api(`/users/${id}/reset-password`, { method: 'POST', body: { new_password: newPassword } })

// --- API keys ---
export const listApiKeys = () => api('/api-keys')
export const createApiKey = (body) => api('/api-keys', { method: 'POST', body })
export const revokeApiKey = (id) => api(`/api-keys/${id}/revoke`, { method: 'POST' })

// --- Audit log ---
export const listAudit = (params = {}) => {
  const q = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== '' && v != null)
  ).toString()
  return api('/audit-logs' + (q ? `?${q}` : ''))
}

// --- Attachments ---
export const listAttachments = (vulnId) => api(`/vulnerabilities/${vulnId}/attachments`)
export function uploadAttachment(vulnId, file, displayName) {
  const form = new FormData()
  form.append('file', file)
  if (displayName) form.append('display_name', displayName)
  return api(`/vulnerabilities/${vulnId}/attachments`, { method: 'POST', body: form })
}
export const deleteAttachment = (id) => api(`/attachments/${id}`, { method: 'DELETE' })

// File content needs the bearer token, so <img src> / <a href> can't point at
// it directly. Fetch it as a Blob and hand out object URLs instead.
export async function fetchAttachmentBlob(id) {
  const res = await authedFetch(`${BASE}/attachments/${id}/content`)
  if (!res.ok) throw new ApiError(res.status, null)
  return res.blob()
}

const blobUrlCache = new Map() // attachment id -> Promise<objectURL>
export function attachmentObjectUrl(id) {
  if (!blobUrlCache.has(id)) {
    blobUrlCache.set(id, fetchAttachmentBlob(id).then((b) => URL.createObjectURL(b))
      .catch((e) => { blobUrlCache.delete(id); throw e }))
  }
  return blobUrlCache.get(id)
}
