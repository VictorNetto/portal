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
export const transitionVuln = (id, to) =>
  api(`/vulnerabilities/${id}/transition`, { method: 'POST', body: { to } })
export const correctVuln = (id, to, reason) =>
  api(`/vulnerabilities/${id}/correction`, { method: 'POST', body: { to, reason } })
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

// --- Reports ---
export const listReports = () => api('/reports')
export const getReport = (id) => api(`/reports/${id}`)
export const createReport = (body) => api('/reports', { method: 'POST', body })
export const updateReport = (id, body) => api(`/reports/${id}`, { method: 'PATCH', body })
export const deleteReport = (id) => api(`/reports/${id}`, { method: 'DELETE' })
export const acquireReportLock = (id) => api(`/reports/${id}/lock`, { method: 'POST' })
export const heartbeatReport = (id) => api(`/reports/${id}/lock/heartbeat`, { method: 'POST' })
export const releaseReportLock = (id) => api(`/reports/${id}/lock`, { method: 'DELETE' })
export const forceReleaseReport = (id) => api(`/reports/${id}/lock/force-release`, { method: 'POST' })
export const addReportSection = (id, body) => api(`/reports/${id}/sections`, { method: 'POST', body })
export const updateReportSection = (id, sid, body) =>
  api(`/reports/${id}/sections/${sid}`, { method: 'PATCH', body })
export const deleteReportSection = (id, sid) =>
  api(`/reports/${id}/sections/${sid}`, { method: 'DELETE' })
export const reorderReportSections = (id, ids) =>
  api(`/reports/${id}/sections/reorder`, { method: 'POST', body: { ids } })
export const createReportVuln = (id, body) =>
  api(`/reports/${id}/vulnerabilities`, { method: 'POST', body })

// Best-effort lock release while the page is closing (a normal fetch may be cancelled).
export function releaseReportLockOnExit(id) {
  if (!accessToken) return
  fetch(`${BASE}/reports/${id}/lock`, {
    method: 'DELETE', keepalive: true, headers: { Authorization: `Bearer ${accessToken}` },
  }).catch(() => {})
}

export const dispatchReport = (id) => api(`/reports/${id}/dispatch`, { method: 'POST' })
export const listReportAttachments = (id) => api(`/reports/${id}/attachments`)
export function uploadReportAttachment(id, file, displayName) {
  const form = new FormData()
  form.append('file', file)
  if (displayName) form.append('display_name', displayName)
  return api(`/reports/${id}/attachments`, { method: 'POST', body: form })
}

// Download a file from an authenticated endpoint (exports): the bearer token
// can't ride on a plain <a href>, so fetch it as a Blob and save that.
export async function downloadAuthed(path, fallbackName) {
  const res = await authedFetch(`${BASE}${path}`)
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new ApiError(res.status, data?.detail)
  }
  const match = /filename="?([^";]+)"?/.exec(res.headers.get('Content-Disposition') || '')
  const url = URL.createObjectURL(await res.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = match ? match[1] : fallbackName
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}
