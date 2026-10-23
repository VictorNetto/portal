// Small UI helpers shared by the specs.
import { expect } from '@playwright/test'

/** Log in through the real login form. Resolves once the Hub list is on screen. */
export async function loginUI(page, username, password) {
  await page.goto('/login')
  await page.fill('input[autocomplete=username]', username)
  await page.fill('input[type=password]', password)
  await page.click('button')
  await expect(page.locator('.vtable')).toBeVisible()
}

/** Answer every portal dialog (the AppDialog modal) and any native one: accept
 *  (prompts get `promptValue`) or, with accept:false, cancel. Returns the list of
 *  dialogs seen as { type, message }. Call before the page navigates. */
export function autoDialogs(page, { promptValue = 'Diagrama', accept = true } = {}) {
  const seen = []
  page.on('dialog', async (d) => {
    seen.push({ type: d.type(), message: d.message() })
    if (!accept) return d.dismiss()
    return d.type() === 'prompt' ? d.accept(promptValue) : d.accept()
  })
  page.exposeBinding('__e2eDialog', (_src, d) => { seen.push(d) })
  const install = ({ accept, promptValue }) => {
    if (window.__e2eDialogsOn) return
    window.__e2eDialogsOn = true
    const answer = (box) => {
      if (box.dataset.e2eDone) return
      box.dataset.e2eDone = '1'
      const input = box.querySelector('input')
      try { window.__e2eDialog({ type: input ? 'prompt' : 'confirm', message: box.querySelector('.dMsg')?.textContent || '' }) } catch { /* binding not ready */ }
      setTimeout(() => {
        if (input && accept) {
          input.value = promptValue
          input.dispatchEvent(new Event('input', { bubbles: true }))
        }
        const btns = box.querySelectorAll('.modalActions .btn')
        ;(accept ? btns[btns.length - 1] : btns[0])?.click()
      }, 50)
    }
    new MutationObserver(() => document.querySelectorAll('.appDialog .modal').forEach(answer))
      .observe(document, { childList: true, subtree: true })
  }
  page.addInitScript(install, { accept, promptValue })                         // pages loaded later
  page.evaluate(install, { accept, promptValue }).catch(() => {})              // the page already open
  page.on('domcontentloaded', () => page.evaluate(install, { accept, promptValue }).catch(() => {}))  // init script may register late
  return seen
}

/** Click a button in the portal dialog (AppDialog) and return its message. */
export async function answerDialog(page, button) {
  const box = page.locator('.appDialog .modal')
  await expect(box).toBeVisible()
  const message = await box.locator('.dMsg').textContent()
  await box.locator('.modalActions .btn', { hasText: button }).click()
  await expect(box).toHaveCount(0)
  return message
}

/** Type into the Hub filter and let the list settle. */
export async function filterHub(page, query) {
  await page.fill('.filterbar input', query)
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)
}

export const rowCount = (page, table = '.vtable') => page.locator(`${table} tbody tr:not(:has(td.empty))`).count()

/** Collect uncaught page errors (the dev-only Vite websocket noise is ignored). */
export function collectPageErrors(page) {
  const errors = []
  page.on('pageerror', (e) => { if (!/WebSocket/.test(e.message)) errors.push(e.message) })
  return errors
}
