import { expect, test } from '@playwright/test'
import { adminToken, cleanup, createUser, newVuln, tag } from '../support/api.js'
import { loginUI } from '../support/ui.js'

let admin
let writer
let other
const vulns = []

test.beforeAll(async () => {
  admin = await adminToken()
  writer = await createUser(admin, 'writer_all')
  other = await createUser(admin, 'writer_all')
})
test.afterAll(async () => cleanup(admin, { vulns }))

test.describe('operator picker', () => {
  test('starts with the logged user; "+" adds others; clicking a selected one removes it', async ({ page }) => {
    await loginUI(page, writer.username, writer.password)
    await page.goto('/vulnerabilities/new')
    const chips = page.locator('.opchips .opchip:not(.plus)')
    await expect(chips).toHaveText([writer.username])
    await expect(chips.first()).toHaveClass(/on/)

    await page.click('.opchip.plus')
    await page.fill('.opsearch', other.username)
    await page.click(`.opitem:has-text("${other.username}")`)
    await expect(chips).toHaveCount(2)                           // order follows the user list
    await expect(page.locator(`.opchip:has-text("${other.username}")`)).toHaveClass(/on/)

    await page.locator(`.opchip:has-text("${other.username}")`).click()                                   // unselect another user: disappears
    await expect(chips).toHaveText([writer.username])
    await chips.first().click()                                  // unselect myself: stays, unselected
    await expect(chips.first()).not.toHaveClass(/on/)
    await expect(chips).toHaveText([writer.username])
  })

  test('a saved vulnerability lists only its operators', async ({ page }) => {
    const v = await newVuln(admin, { identifier: `e2e-op-${tag()}`, operator_ids: [other.id] })
    vulns.push(v.id)
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    const chips = page.locator('.opchips .opchip:not(.plus)')
    await expect(chips).toHaveCount(2)                           // me (unselected, always visible) + the operator
    await expect(page.locator(`.opchip:has-text("${other.username}")`)).toHaveClass(/on/)
    await expect(page.locator(`.opchip:has-text("${writer.username}")`)).not.toHaveClass(/on/)
  })
})

test.describe('read-only role', () => {
  test('edition buttons are disabled, not just hidden-by-error', async ({ page }) => {
    const reader = await createUser(admin, 'reader_all')
    const v = await newVuln(admin, { identifier: `e2e-ro-${tag()}` })
    vulns.push(v.id)
    await loginUI(page, reader.username, reader.password)
    await expect(page.locator('.btn.primary:has-text("Criar")')).toBeDisabled()
    await page.goto(`/vulnerabilities/${v.id}`)
    await expect(page.locator('.pageActions .btn.primary')).toBeDisabled()
    await expect(page.locator('.pageActions .btn.danger')).toBeDisabled()
    await expect(page.locator('.infoGrid input').first()).toBeDisabled()
    await page.goto('/reports/new')
    await expect(page.locator('.createCard .btn.primary')).toBeDisabled()
  })
})
