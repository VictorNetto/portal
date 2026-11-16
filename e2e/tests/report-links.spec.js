import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, login, newReport, newVuln, savedVuln, tag } from '../support/api.js'
import { autoDialogs, collectPageErrors, loginUI } from '../support/ui.js'

let admin
let alice
const reports = []
const vulns = []

test.beforeAll(async () => {
  admin = await adminToken()
  alice = await createUser(admin, 'write_all')
  alice.token = await login(alice.username, alice.password)
})
test.afterAll(async () => cleanup(admin, { reports, vulns }))

test.describe('linking vulnerabilities to a report', () => {
  test('link existing vulnerabilities, then unlink one', async ({ page }) => {
    const errors = collectPageErrors(page)
    autoDialogs(page)
    const u = tag()
    const report = await newReport(alice.token, { name: `e2e-link-${u}` })
    reports.push(report.id)
    const draft = await newVuln(alice.token, { identifier: `e2e-link-${u}-draft` })
    const ready = await savedVuln(alice.token, { identifier: `e2e-link-${u}-ready` })
    vulns.push(draft.id, ready.id)

    await loginUI(page, alice.username, alice.password)
    await page.goto(`/reports/${report.id}`)
    await expect(page.locator('.banner.mine')).toBeVisible()

    // the picker lists standalone vulns not sent yet; the search narrows it
    await page.getByRole('button', { name: 'Vincular', exact: true }).click()
    const modal = page.locator('.linkModal')
    await modal.locator('.linkSearch').fill(`e2e-link-${u}`)
    await expect(modal.locator('.linkList li')).toHaveCount(2)
    await modal.locator('label', { hasText: `${u}-draft` }).locator('input').check()
    await modal.locator('label', { hasText: `${u}-ready` }).locator('input').check()
    await modal.getByRole('button', { name: 'Vincular (2)' }).click()
    await expect(modal).toBeHidden()

    const rows = page.locator('.vt tbody tr')
    await expect(rows).toHaveCount(2)
    await expect(page.locator('.vt tbody tr', { hasText: `${u}-ready` }).locator('.pill')).toHaveText('Rascunho')

    // unlink: it becomes a standalone draft again
    await page.locator('.vt tbody tr', { hasText: `${u}-draft` }).getByRole('button', { name: 'Desvincular' }).click()
    await expect(rows).toHaveCount(1)
    const back = await api(`/vulnerabilities/${draft.id}`, { token: alice.token })
    expect(back.data.report_id).toBeNull()
    expect(errors).toEqual([])
  })

  test('without the lock there is nothing to link or unlink', async ({ page }) => {
    const report = await newReport(alice.token, { name: `e2e-link-${tag()}` })
    reports.push(report.id)
    await api(`/reports/${report.id}/lock`, { token: alice.token, method: 'DELETE' })
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/reports/${report.id}`)
    await expect(page.locator('.pageActions .btn.primary', { hasText: 'Editar' })).toBeVisible()   // free: offered to take the lock
    await expect(page.getByRole('button', { name: 'Vincular', exact: true })).toHaveCount(0)
  })
})

test.describe('long texts', () => {
  test('an editor expands to the window and collapses again; notes do not expand', async ({ page }) => {
    const v = await newVuln(alice.token, { identifier: `e2e-expand-${tag()}` })
    vulns.push(v.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    const editor = page.locator('.mdEditor').first()
    const area = editor.locator('textarea')
    const before = (await area.boundingBox()).height
    await editor.getByRole('button', { name: 'Expandir' }).click()
    await expect.poll(async () => (await area.boundingBox()).height).toBeGreaterThan(before + 200)
    if (process.env.E2E_SHOTS) { await page.waitForTimeout(800); await page.screenshot({ path: `${process.env.E2E_SHOTS}/editor-expanded.png` }) }
    await area.press('Escape')
    await expect.poll(async () => (await area.boundingBox()).height).toBe(before)
    // Mitigação / Solução expands too; the internal notes editor has no button
    await expect(page.getByRole('button', { name: 'Expandir' })).toHaveCount(3)
  })

  test('mitigation can be left blank when completing', async ({ page }) => {
    autoDialogs(page)
    const v = await newVuln(alice.token, { identifier: `e2e-nomit-${tag()}`, mitigation: '' })
    vulns.push(v.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    await page.getByRole('button', { name: 'Concluir' }).click()
    await expect.poll(async () => (await api(`/vulnerabilities/${v.id}`, { token: alice.token })).data.status).toBe('ready')
  })
})
