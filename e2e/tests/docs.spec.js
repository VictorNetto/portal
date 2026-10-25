import { expect, test } from '@playwright/test'
import { adminToken, createUser } from '../support/api.js'
import { loginUI } from '../support/ui.js'

test.describe('documentation', () => {
  test('opens from the profile menu; the contents jump to a topic', async ({ page }) => {
    await loginUI(page, 'admin', 'admin')
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Documentação")')
    await expect(page).toHaveURL(/\/docs$/)
    await expect(page.locator('.titleBlock h1')).toHaveText('Documentação')
    await expect(page.locator('.docCard h2')).toContainText(['Primeiros passos', 'Sessão', 'Templates', 'Administração', 'Logs de auditoria'])
    await page.click('.toc .tocItem:has-text("Fila RVS")')
    await expect(page).toHaveURL(/\/docs#rvs$/)
    await expect(page.locator('#doc-rvs')).toBeInViewport()
    await expect(page.locator('.toc .tocItem.current')).toHaveText('Fila RVS')
  })

  test('a reader sees only the topics for what they can use, in their language', async ({ page }) => {
    const reader = await createUser(await adminToken(), 'read_all')
    await loginUI(page, reader.username, reader.password)
    await page.goto('/docs#sessao')
    await expect(page.locator('#doc-sessao')).toBeInViewport()
    const titles = page.locator('.docCard h2')
    await expect(titles).toContainText(['Vulnerabilidades', 'Relatórios'])
    for (const hidden of ['Templates', 'Administração', 'Logs de auditoria']) {
      await expect(page.locator(`.docCard h2:text-is("${hidden}")`)).toHaveCount(0)
    }
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("English")')
    await expect(page.locator('.titleBlock h1')).toHaveText('Documentation')
    await expect(titles.first()).toHaveText('Getting started')
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Português")')
  })
})
