import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, fixingVuln, newReport, reportVuln, savedVuln, tag } from '../support/api.js'
import { autoDialogs, loginUI } from '../support/ui.js'

let admin
let writer
const vulns = []

test.beforeAll(async () => {
  admin = await adminToken()
  writer = await createUser(admin, 'write_all')
})
test.afterAll(async () => cleanup(admin, { vulns }))

const status = (page) => page.locator('.titleBlock p')
const current = (page) => page.locator('.timeline .step.current .label')

test.describe('vulnerability lifecycle', () => {
  test('a sent report shows its progress, then Concluído when everything is fixed', async ({ page }) => {
    const r = await newReport(admin, { name: `e2e-prog-${tag()}` })
    const a = await reportVuln(admin, r.id)
    const b = await reportVuln(admin, r.id)
    await api(`/reports/${r.id}/lock`, { token: admin, method: 'POST' })
    const sent = await api(`/reports/${r.id}/send`, { token: admin, method: 'POST' })
    expect(sent.status).toBe(200)
    const fix = async (v) => {
      await api(`/vulnerabilities/${v.id}/rvs`, { token: admin, body: { rvs_id: `RVS-e2e-${tag()}` } })
      await api(`/vulnerabilities/${v.id}/transition`, { token: admin, body: { to: 'retesting' } })
      await api(`/vulnerabilities/${v.id}/transition`, { token: admin, body: { to: 'fixed' } })
    }
    await fix(a)
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/reports/${r.id}`)
    await expect(page.locator('.subline .pill')).toHaveText('Enviado')
    await expect(page.locator('.subline')).toContainText('1 de 2 corrigidas')
    await fix(b)
    await page.reload()
    await expect(page.locator('.subline .pill')).toHaveText('Concluído')
    await expect(page.locator('.subline')).not.toContainText('corrigidas')
  })

  test('RVS queue: registering an id starts the fix', async ({ page }) => {
    const v = await savedVuln(admin, { identifier: `e2e-rvs-${tag()}` })
    vulns.push(v.id)
    await (await fetch(`${process.env.E2E_BASE_URL || 'http://nginx:80'}/api/vulnerabilities/${v.id}/send`, {
      method: 'POST', headers: { Authorization: `Bearer ${admin}` },
    })).text()

    await loginUI(page, writer.username, writer.password)
    await page.locator('.sidebar .navItem[aria-label="Fila RVS"]').click()
    const row = page.locator(`tbody tr:has-text("${v.internal_id}")`)
    await expect(row).toBeVisible()
    await row.locator('input').fill('RVS-e2e-777')
    await row.locator('button').click()
    await expect(row).toHaveCount(0)                                   // it left the queue

    await page.goto(`/vulnerabilities/${v.id}`)
    await expect(status(page)).toContainText('Em correção')
    await expect(page.locator('.timeline .rvs')).toHaveText('RVS-e2e-777')
  })

  test('fixing -> retesting (fail, then pass) -> fixed', async ({ page }) => {
    const v = await fixingVuln(admin, { identifier: `e2e-lc-${tag()}` })
    vulns.push(v.id)
    autoDialogs(page)
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/vulnerabilities/${v.id}`)

    await expect(page.locator('.pageActions button:has-text("Ajustar status")')).toHaveCount(0)   // admins only
    await expect(status(page)).toContainText('Em correção')
    await page.click('button:has-text("Solicitar reteste")')
    await expect(status(page)).toContainText('Em reteste')
    await expect(page.locator('button:has-text("Aprovar reteste")')).toBeVisible()
    await page.click('button:has-text("Reprovar reteste")')
    await expect(status(page)).toContainText('Em correção')                    // the loop
    await page.click('button:has-text("Solicitar reteste")')
    await page.click('button:has-text("Aprovar reteste")')
    await expect(status(page)).toContainText('Corrigida')
    await expect(current(page)).toHaveText('Corrigida')
    await expect(page.locator('button:has-text("reteste")')).toHaveCount(0)    // nothing left to do
  })

  test('an admin can correct a mistaken status, which also clears the RVS id', async ({ page }) => {
    const v = await fixingVuln(admin, { identifier: `e2e-corr-${tag()}` })
    vulns.push(v.id)
    autoDialogs(page)
    await loginUI(page, 'admin', 'admin')
    await page.goto(`/vulnerabilities/${v.id}`)

    await page.click('button:has-text("Ajustar status")')
    await expect(page.locator('.correction .btn.primary')).toBeDisabled()       // a reason is mandatory
    await page.selectOption('.correction select', 'sent')
    await page.fill('.correction input', 'RVS id was entered wrongly')
    await page.click('.correction .btn.primary')

    await expect(status(page)).toContainText('Enviada')
    await expect(page.locator('.timeline .rvs')).toHaveCount(0)
    await expect(page.locator('.timeline .step.reached')).toHaveCount(3)

    // it is back in the RVS queue
    await page.locator('.sidebar .navItem[aria-label="Fila RVS"]').click()
    await expect(page.locator(`tbody tr:has-text("${v.internal_id}")`)).toBeVisible()
  })
})
