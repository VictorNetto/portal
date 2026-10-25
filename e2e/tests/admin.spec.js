import { expect, test } from '@playwright/test'
import { adminToken, api, createUser, login, newVuln, tag } from '../support/api.js'
import { autoDialogs, loginUI } from '../support/ui.js'

let admin

test.beforeAll(async () => { admin = await adminToken() })

const nav = (page, label) => page.locator(`.sidebar .navItem[aria-label="${label}"]`)

test.describe('administration', () => {
  test('users: create one (forced password change), change role, reset, deactivate', async ({ page }) => {
    autoDialogs(page, { promptValue: 'Reset-By-Admin-1' })
    await loginUI(page, 'admin', 'admin')
    await nav(page, 'Usuários').click()
    await expect(page.locator('table').first()).toBeVisible()

    const username = `e2e-new-${tag()}`
    await page.click('.pageTop .btn.primary')                                 // Novo usuário
    await page.locator('.formRow input').first().fill(username)
    await page.locator('.formRow input[type=password]').fill('Temp-Pass-1234')
    await page.locator('.formRow select').selectOption('write_all')
    await page.click('.formActions .btn.primary')

    // the new user is opened in the detail panel
    const detail = page.locator('.detail')
    await expect(detail.locator('.dName')).toHaveText(username)
    await expect(detail.locator('.flag')).toBeVisible()                        // "troca obrigatória"
    await expect(page.locator(`tbody tr:has-text("${username}") .flag`)).toBeVisible()

    await detail.locator('select.roleSel').selectOption('read_restricted')
    await expect(detail.locator('select.roleSel')).toHaveValue('read_restricted')
    await expect(page.locator(`tbody tr:has-text("${username}")`)).toContainText('Leitor restrito')

    await detail.locator('.btn:has-text("Redefinir senha")').click()
    await expect(detail.locator('.flag')).toBeVisible()
    await detail.locator('.btn:has-text("Desativar")').click()
    await expect(detail.locator('.dHead .pill')).toHaveText('Inativo')
    await expect(page.locator(`tbody tr:has-text("${username}") .pill`)).toHaveText('Inativo')
    expect((await api('/auth/login', { body: { username, password: 'Reset-By-Admin-1' } })).status).toBe(401)
  })

  test('users: search and filters narrow the list; the selection lives in the URL', async ({ page }) => {
    const a = await createUser(admin, 'read_restricted')
    const b = await createUser(admin, 'write_restricted')
    await loginUI(page, 'admin', 'admin')
    await nav(page, 'Usuários').click()

    await page.fill('.search', 'e2e-readrestricted')
    await expect(page.locator(`tbody tr:has-text("${a.username}")`)).toHaveCount(1)
    await expect(page.locator(`tbody tr:has-text("${b.username}")`)).toHaveCount(0)
    await page.fill('.search', 'e2e-')
    await page.locator('.toolbar select').first().selectOption('write_restricted')
    await expect(page.locator(`tbody tr:has-text("${b.username}")`)).toHaveCount(1)
    await expect(page.locator(`tbody tr:has-text("${a.username}")`)).toHaveCount(0)

    await page.click(`tbody tr:has-text("${b.username}")`)
    await expect(page).toHaveURL(new RegExp(`user=${b.id}`))
    await page.reload()
    await expect(page.locator('.detail .dName')).toHaveText(b.username)
  })

  test('users: the admin sees which records a restricted user can reach, and why', async ({ page }) => {
    const reader = await createUser(admin, 'read_restricted')
    const shared = await newVuln(admin, { identifier: `e2e-acc-${tag()}-shared`, viewer_ids: [reader.id] })
    const operated = await newVuln(admin, { identifier: `e2e-acc-${tag()}-operated`, operator_ids: [reader.id] })
    const hidden = await newVuln(admin, { identifier: `e2e-acc-${tag()}-hidden` })
    await loginUI(page, 'admin', 'admin')
    await page.goto(`/users?user=${reader.id}`)

    const rows = page.locator('.accessList tbody tr')
    await expect(rows).toHaveCount(2)
    await expect(page.locator(`.accessList tr:has-text("${shared.identifier}")`)).toContainText('Compartilhado')
    await expect(page.locator(`.accessList tr:has-text("${operated.identifier}")`)).toContainText('Operador')
    await expect(page.locator('.accessList')).not.toContainText(hidden.identifier)
    await expect(page.locator('.accessBox .tab').nth(1)).toContainText('(0)')

    // a role that reads everything has no list
    const writer = await createUser(admin, 'write_all')
    await page.goto(`/users?user=${writer.id}`)
    await expect(page.locator('.accessBox')).toContainText('todos os registros')
    for (const v of [shared, operated, hidden]) await api(`/vulnerabilities/${v.id}`, { token: admin, method: 'DELETE' })
  })

  test('an admin cannot deactivate themselves: the button is not offered', async ({ page }) => {
    await loginUI(page, 'admin', 'admin')
    await nav(page, 'Usuários').click()
    await page.click('tbody tr:has(td.uname:text-is("admin"))')
    await expect(page.locator('.detail .dName')).toHaveText('admin')
    await expect(page.locator('.detail .btn:has-text("Desativar")')).toHaveCount(0)
    await expect(page.locator('.detail select.roleSel')).toHaveCount(0)
  })

  test('API keys: the plaintext is shown once, then only the prefix; revoking works', async ({ page }) => {
    autoDialogs(page)
    await loginUI(page, 'admin', 'admin')
    await nav(page, 'Chaves de API').click()

    const label = `e2e-key-${tag()}`
    await page.click('.pageTop .btn.primary')
    await page.locator('.formRow input').first().fill(label)
    await expect(page.locator('.formActions .btn.primary')).toBeDisabled()       // at least one permission
    await page.locator('.scope', { hasText: 'vulns:write' }).locator('input').check()
    await page.click('.formActions .btn.primary')

    const reveal = page.locator('.keyReveal')
    await expect(reveal).toBeVisible()
    const plaintext = (await reveal.locator('.plaintext').innerText()).trim()
    expect(plaintext.length).toBeGreaterThanOrEqual(32)
    await reveal.locator('.btn.primary').click()                                // "Pronto" hides it for good
    await expect(reveal).toHaveCount(0)
    await page.reload()
    await expect(page.locator('body')).not.toContainText(plaintext)

    const row = page.locator(`tbody tr:has-text("${label}")`)
    await expect(row).toContainText(plaintext.slice(0, 8))                      // only the prefix is kept
    await expect(row.locator('.pill')).toHaveText('Ativa')
    await expect(row.locator('.scopeTag')).toHaveText(['vulns:write'])
    const ingest = (key) => fetch(`${process.env.E2E_BASE_URL || 'http://nginx:80'}/api/ingest/vulnerabilities`, {
      method: 'POST', headers: { 'X-API-Key': key, 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier: `e2e-ingest-${tag()}` }),
    })
    expect((await ingest(plaintext)).status).toBe(201)                          // the key works...
    await row.locator('.link:has-text("Revogar")').click()
    await expect(row.locator('.pill')).toHaveText('Revogada')
    expect((await ingest(plaintext)).status).toBe(401)                          // ...until it is revoked
  })

  test('audit log: filter by action and see who did it', async ({ page }) => {
    const user = await createUser(admin, 'write_all')
    await login(user.username, user.password)
    await loginUI(page, 'admin', 'admin')
    await nav(page, 'Logs de Auditoria').click()
    await expect(page.locator('tbody tr').first()).toBeVisible()

    await page.selectOption('.pageTop select', 'login')
    await expect(page.locator('tbody .act').first()).toHaveText('login')
    // the filtered list replaces the unfiltered one asynchronously: wait for it to settle
    await expect.poll(() => page.locator('tbody .act').evaluateAll((els) => els.every((e) => e.textContent === 'login'))).toBe(true)
    await expect(page.locator('tbody')).toContainText(user.username)
    await expect(page.locator('.pageInfo').first()).toContainText('registros')
  })

  test('the audit log is not reachable by a writer', async ({ page }) => {
    const user = await createUser(admin, 'write_all')
    await loginUI(page, user.username, user.password)
    await expect(nav(page, 'Logs de Auditoria')).toHaveCount(0)
    await page.goto('/audit-logs')
    await expect(page).toHaveURL(/\/hub/)
  })
})
