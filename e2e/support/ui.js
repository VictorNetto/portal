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

/** Accept every confirm()/alert(); answer prompt() with `promptValue`. */
export function autoDialogs(page, { promptValue = 'Diagrama', accept = true } = {}) {
  const seen = []
  page.on('dialog', async (d) => {
    seen.push({ type: d.type(), message: d.message() })
    if (!accept) return d.dismiss()
    return d.type() === 'prompt' ? d.accept(promptValue) : d.accept()
  })
  return seen
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
