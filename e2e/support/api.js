// Test helpers that talk to the API directly (fast setup, independent of the UI).
import { randomBytes } from 'node:crypto'
import { deflateSync } from 'node:zlib'

const BASE = process.env.E2E_BASE_URL || 'http://nginx:80'
export const ADMIN = {
  username: process.env.E2E_ADMIN_USER || 'admin',
  password: process.env.E2E_ADMIN_PASSWORD || '12345678',
}

export const tag = () => randomBytes(4).toString('hex')

export async function api(path, { token, method, body } = {}) {
  const res = await fetch(`${BASE}/api${path}`, {
    method: method || (body !== undefined ? 'POST' : 'GET'),
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => null)
  return { status: res.status, data }
}

export async function login(username, password) {
  const { status, data } = await api('/auth/login', { body: { username, password } })
  if (status !== 200) throw new Error(`login failed for ${username}: ${status}`)
  return data.access_token
}

export const adminToken = () => login(ADMIN.username, ADMIN.password)

/** A user as a real one starts: temporary password, forced change, then ready to use. */
export async function createUser(adminTok, role, { finishFirstLogin = true } = {}) {
  const username = `e2e-${role.replace('_', '')}-${tag()}`
  const temp = `Temp-${tag()}-1`
  const final = `Final-${tag()}-1`
  const { status, data } = await api('/users', { token: adminTok, body: { username, password: temp, role } })
  if (status !== 201) throw new Error(`createUser failed: ${status}`)
  let password = temp
  if (finishFirstLogin) {
    const t = await login(username, temp)
    await api('/auth/change-password', { token: t, body: { current_password: temp, new_password: final } })
    password = final
  }
  return { id: data.id, username, password, role }
}

export async function newVuln(token, fields = {}) {
  const { status, data } = await api('/vulnerabilities', {
    token, body: { identifier: `e2e-${tag()}`, description: 'd', finding_detail: 'f', mitigation: 'm', ...fields },
  })
  if (status !== 201) throw new Error(`newVuln failed: ${status}`)
  return data
}

export async function savedVuln(token, fields = {}) {
  const v = await newVuln(token, fields)
  const { status, data } = await api(`/vulnerabilities/${v.id}/send`, { token, method: 'POST' })
  if (status !== 200) throw new Error(`send failed: ${status} ${JSON.stringify(data)}`)
  return data
}

export async function acknowledgedVuln(token, fields = {}) {
  const v = await savedVuln(token, fields)
  await api(`/vulnerabilities/${v.id}/dispatch`, { token, method: 'POST' })
  const { data } = await api(`/vulnerabilities/${v.id}/rvs`, { token, body: { rvs_id: `RVS-e2e-${tag()}` } })
  return data
}

export async function newReport(token, fields = {}) {
  const { status, data } = await api('/reports', { token, body: { name: `e2e-${tag()}`, ...fields } })
  if (status !== 201) throw new Error(`newReport failed: ${status}`)
  return data
}

export async function reportVuln(token, reportId, fields = {}) {
  const { status, data } = await api(`/reports/${reportId}/vulnerabilities`, {
    token, body: { identifier: `e2e-${tag()}`, description: 'd', ...fields },
  })
  if (status !== 201) throw new Error(`reportVuln failed: ${status}`)
  return data
}

/** Best-effort cleanup of what a test created (soft deletes; dispatched reports stay). */
export async function cleanup(token, { vulns = [], reports = [] } = {}) {
  for (const id of vulns) await api(`/vulnerabilities/${id}`, { token, method: 'DELETE' })
  for (const id of reports) {
    await api(`/reports/${id}/lock`, { token, method: 'DELETE' })
    await api(`/reports/${id}`, { token, method: 'DELETE' })
  }
}

// --- fixtures generated in code (no files to carry around) ---
function crc32(buf) {
  let c, crc = 0xffffffff
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xff
    for (let k = 0; k < 8; k++) c = c & 1 ? (c >>> 1) ^ 0xedb88320 : c >>> 1
    crc = (crc >>> 8) ^ c
  }
  return (crc ^ 0xffffffff) >>> 0
}

export function pngBuffer(w = 24, h = 16, rgb = [30, 120, 220]) {
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length)
    const body = Buffer.concat([Buffer.from(type), data])
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body))
    return Buffer.concat([len, body, crc])
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2
  const row = Buffer.concat([Buffer.from([0]), Buffer.from(Array(w).fill(rgb).flat())])
  const raw = Buffer.concat(Array(h).fill(row))
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw)), chunk('IEND', Buffer.alloc(0))])
}

export const pdfBuffer = () => Buffer.from('%PDF-1.4\n%e2e evidence\n')
export const textFile = (name = 'log.txt') => ({ name, mimeType: 'text/plain', buffer: Buffer.from('request log\n') })
export const pngFile = (name = 'shot.png') => ({ name, mimeType: 'image/png', buffer: pngBuffer() })
export const pdfFile = (name = 'evidence.pdf') => ({ name, mimeType: 'application/pdf', buffer: pdfBuffer() })
