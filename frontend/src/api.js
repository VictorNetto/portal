// Thin fetch wrapper for the backend API. All calls go through nginx at /api,
// so the frontend never needs to know the backend's address.

const BASE = '/api'

let accessToken = null
export function setAccessToken(token) {
  accessToken = token
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

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
