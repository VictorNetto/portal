import { expect, test } from '@playwright/test'
import { adminToken, createUser } from '../support/api.js'
import { loginUI } from '../support/ui.js'

// The browser clock is faked so 15 idle minutes pass in a moment (D12).
let writer
test.beforeAll(async () => { writer = await createUser(await adminToken(), 'write_all') })

const MIN = 60 * 1000
async function signedIn(page) {
  await page.clock.install()
  await loginUI(page, writer.username, writer.password)
}
const sessionModal = (page) => page.locator('.sessionModal .modal')

test.describe('session limits', () => {
  test('after 13 idle minutes the user is asked; "Continuar conectado" keeps the session', async ({ page }) => {
    await signedIn(page)
    await page.clock.fastForward(12 * MIN)
    await expect(sessionModal(page)).toHaveCount(0)
    await page.clock.fastForward(1.1 * MIN)
    await expect(sessionModal(page)).toContainText('Você ainda está aí?')
    await expect(sessionModal(page)).toContainText(/encerrada em 1:\d\d/)
    await sessionModal(page).locator('.btn', { hasText: 'Continuar conectado' }).click()
    await expect(sessionModal(page)).toHaveCount(0)
    await page.clock.fastForward(10 * MIN)                                    // the clock restarted
    await expect(sessionModal(page)).toHaveCount(0)
    await expect(page).toHaveURL(/\/hub/)
  })

  test('15 idle minutes with nothing unsaved: back to the login page, saying why', async ({ page }) => {
    await signedIn(page)
    await page.clock.fastForward(15.1 * MIN)
    await expect(page).toHaveURL(/\/login\?expired=idle/)
    await expect(page.locator('.notice')).toHaveText('Sua sessão foi encerrada por inatividade.')
    expect(await page.evaluate(() => localStorage.getItem('rtp_access'))).toBeNull()
  })

  test('the session ends with unsaved edits: sign in again in the modal, then save them', async ({ page }) => {
    await signedIn(page)
    await page.goto('/vulnerabilities/new')
    const ident = `e2e-sess-${Date.now()}`
    await page.locator('.infoGrid input').first().fill(ident)
    await page.clock.fastForward(15.1 * MIN)                                  // typing stopped 15 min ago
    const modal = sessionModal(page)
    await expect(modal).toContainText('Sessão encerrada')
    await expect(modal).toContainText(writer.username)
    await expect(page).toHaveURL(/\/vulnerabilities\/new$/)                    // the page (and the edit) is kept

    await modal.locator('input[type=password]').fill('wrong-password')
    await modal.locator('.btn.primary').click()
    await expect(modal.locator('.err')).toHaveText('Senha incorreta.')
    await modal.locator('input[type=password]').fill(writer.password)
    await modal.locator('.btn.primary').click()
    await expect(modal).toHaveCount(0)
    await expect(page.locator('.infoGrid input').first()).toHaveValue(ident)

    await page.click('.pageActions button:has-text("Salvar rascunho")')
    await expect(page).toHaveURL(/\/vulnerabilities\/[0-9a-f-]{36}$/)
  })

  test('discarding the unsaved edits leaves without asking again', async ({ page }) => {
    await signedIn(page)
    await page.goto('/vulnerabilities/new')
    await page.locator('.infoGrid input').first().fill('e2e-sess-discard')
    await page.clock.fastForward(15.1 * MIN)
    await sessionModal(page).locator('.btn', { hasText: 'Descartar e sair' }).click()
    await expect(page).toHaveURL(/\/login\?expired=idle/)
    await expect(page.locator('.appDialog')).toHaveCount(0)                    // no "unsaved changes" question
  })

  test('five minutes before the 1 h limit the user is told to save', async ({ page }) => {
    await signedIn(page)
    // jump the session's start back 56 minutes (activity keeps it from idling out)
    await page.evaluate(() => localStorage.setItem('rtp_session_end', String(Date.now() + 4 * 60 * 1000)))
    await page.reload()
    await page.clock.fastForward(2000)
    await expect(sessionModal(page)).toContainText('Sua sessão está terminando')
    await expect(sessionModal(page)).toContainText(/termina em [34]:\d\d/)
    await sessionModal(page).locator('.btn', { hasText: 'Entendi' }).click()
    await expect(sessionModal(page)).toHaveCount(0)
  })

  test('confirmations use the portal modal, not the browser dialog', async ({ page }) => {
    let native = 0
    page.on('dialog', (d) => { native++; d.dismiss() })
    await loginUI(page, writer.username, writer.password)
    await page.goto('/vulnerabilities/new')
    await page.locator('.infoGrid input').first().fill('e2e-unsaved')
    await page.click('.pageActions button:has-text("Cancelar")')
    const box = page.locator('.appDialog .modal')
    await expect(box).toContainText('alterações não salvas')
    await expect(box.locator('.btn')).toHaveText(['Cancelar', 'Sair sem salvar'])
    await box.locator('.btn', { hasText: 'Cancelar' }).click()
    await expect(page).toHaveURL(/\/vulnerabilities\/new$/)
    await page.click('.pageActions button:has-text("Cancelar")')
    await box.locator('.btn', { hasText: 'Sair sem salvar' }).click()
    await expect(page).toHaveURL(/\/hub/)
    expect(native).toBe(0)
  })
})
