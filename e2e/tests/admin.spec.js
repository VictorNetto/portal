import { expect, test } from '@playwright/test'
import { adminToken, api, createUser, login, tag } from '../support/api.js'
import { autoDialogs, loginUI } from '../support/ui.js'

let admin

test.beforeAll(async () => { admin = await adminToken() })

const nav = (page, label) => page.locator(`.sidebar .navItem[aria-label="${label}"]`)

test.describe('administration', () => {
  test('users: create one (forced password change), change role, reset, deactivate', async ({ page }) => {
    autoDialogs(page, { promptValue: 'Reset-By-Admin-1' })
    await loginUI(page, 'admin', '12345678')
    await nav(page, 'Usuários').click()
    await expect(page.locator('table')).toBeVisible()

    const username = `e2e-new-${tag()}`
    await page.click('.pageTop .btn.primary')                                 // Novo usuário
    await page.locator('.formRow input').first().fill(username)
    await page.locator('.formRow input[type=password]').fill('Temp-Pass-1234')
    await page.locator('.formRow select').selectOption('write_all')
    await page.click('.formActions .btn.primary')

    const row = page.locator(`tbody tr:has-text("${username}")`)
    await expect(row).toBeVisible()
    await expect(row.locator('.flag')).toBeVisible()                           // "troca obrigatória"

    await row.locator('select').selectOption('read_all')
    await expect(row.locator('select')).toHaveValue('read_all')

    await row.locator('.link:has-text("Redefinir senha")').click()
    await expect(row.locator('.flag')).toBeVisible()
    await row.locator('.link:has-text("Desativar")').click()
    await expect(row.locator('.pill')).toHaveText('Inativo')
    expect((await api('/auth/login', { body: { username, password: 'Reset-By-Admin-1' } })).status).toBe(401)
  })

  test('an admin cannot deactivate themselves from the UI', async ({ page }) => {
    await loginUI(page, 'admin', '12345678')
    await nav(page, 'Usuários').click()
    await page.locator('tbody tr:has(td.uname:text-is("admin")) .link:has-text("Desativar")').click()
    await expect(page.locator('.err')).toBeVisible()
  })

  test('API keys: the plaintext is shown once, then only the prefix; revoking works', async ({ page }) => {
    autoDialogs(page)
    await loginUI(page, 'admin', '12345678')
    await nav(page, 'Chaves de API').click()

    const label = `e2e-key-${tag()}`
    await page.click('.pageTop .btn.primary')
    await page.locator('.formRow input').first().fill(label)
    await page.locator('.formRow select').selectOption('write_all')
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
    await loginUI(page, 'admin', '12345678')
    await nav(page, 'Logs de Auditoria').click()
    await expect(page.locator('tbody tr').first()).toBeVisible()

    await page.selectOption('.pageTop select', 'login')
    await expect(page.locator('tbody .act').first()).toHaveText('login')
    expect(await page.locator('tbody .act').evaluateAll((els) => els.every((e) => e.textContent === 'login'))).toBe(true)
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
