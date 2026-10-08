import { expect, test } from '@playwright/test'
import { acknowledgedVuln, adminToken, cleanup, createUser, savedVuln, tag } from '../support/api.js'
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
  test('RVS queue: registering an id acknowledges the vulnerability', async ({ page }) => {
    const v = await savedVuln(admin, { identifier: `e2e-rvs-${tag()}` })
    vulns.push(v.id)
    await (await fetch(`${process.env.E2E_BASE_URL || 'http://nginx:80'}/api/vulnerabilities/${v.id}/dispatch`, {
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
    await expect(status(page)).toContainText('Reconhecida')
    await expect(page.locator('.timeline .rvs')).toHaveText('RVS-e2e-777')
  })

  test('acknowledged -> waiting fix -> retest (fail, then pass) -> fixed', async ({ page }) => {
    const v = await acknowledgedVuln(admin, { identifier: `e2e-lc-${tag()}` })
    vulns.push(v.id)
    autoDialogs(page)
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/vulnerabilities/${v.id}`)

    await expect(page.locator('.pageActions button:has-text("Corrigir status")')).toHaveCount(0)   // admins only
    await page.click('button:has-text("Marcar aguardando correção")')
    await expect(status(page)).toContainText('Aguardando correção')
    await page.click('button:has-text("Enviar para reteste")')
    await expect(status(page)).toContainText('Reteste pendente')
    await expect(page.locator('button:has-text("Reteste reprovado")')).toBeVisible()
    await page.click('button:has-text("Reteste reprovado")')
    await expect(status(page)).toContainText('Aguardando correção')            // the loop
    await page.click('button:has-text("Enviar para reteste")')
    await page.click('button:has-text("Reteste aprovado")')
    await expect(status(page)).toContainText('Corrigida')
    await expect(current(page)).toHaveText('Corrigida')
    await expect(page.locator('button:has-text("Reteste")')).toHaveCount(0)    // nothing left to do
  })

  test('an admin can correct a mistaken status, which also clears the RVS id', async ({ page }) => {
    const v = await acknowledgedVuln(admin, { identifier: `e2e-corr-${tag()}` })
    vulns.push(v.id)
    autoDialogs(page)
    await loginUI(page, 'admin', '12345678')
    await page.goto(`/vulnerabilities/${v.id}`)

    await page.click('button:has-text("Corrigir status")')
    await expect(page.locator('.correction .btn.primary')).toBeDisabled()       // a reason is mandatory
    await page.selectOption('.correction select', 'dispatched')
    await page.fill('.correction input', 'RVS id was entered wrongly')
    await page.click('.correction .btn.primary')

    await expect(status(page)).toContainText('Disparada')
    await expect(page.locator('.timeline .rvs')).toHaveCount(0)
    await expect(page.locator('.timeline .step.reached')).toHaveCount(3)

    // it is back in the RVS queue
    await page.locator('.sidebar .navItem[aria-label="Fila RVS"]').click()
    await expect(page.locator(`tbody tr:has-text("${v.internal_id}")`)).toBeVisible()
  })
})
