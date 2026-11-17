// A user's full name and display name: set on Perfil, shown to others instead of the login.
import { test, expect } from '@playwright/test'
import { adminToken, createUser, newVuln, cleanup, tag } from '../support/api.js'
import { loginUI } from '../support/ui.js'

test.describe('profile names', () => {
  test('the user sets their names and others see the display name', async ({ page, browser }) => {
    const admin = await adminToken()
    const user = await createUser(admin, 'write_all')
    await loginUI(page, user.username, user.password)
    await expect(page.locator('.profileBtn')).toHaveText(user.username)   // no name yet: the login

    await page.goto('/profile')
    const card = page.locator('.namesCard')
    const save = card.locator('button.primary')
    await expect(save).toBeDisabled()
    await card.locator('input[autocomplete=name]').fill('Beatriz Alves Costa')
    await card.locator('input[autocomplete=nickname]').fill('Bia')
    await save.click()
    await expect(card.locator('.ok')).toHaveText('Nome salvo.')
    await expect(save).toBeDisabled()
    await expect(page.locator('.profileBtn')).toHaveText('Bia')
    await page.reload()
    await expect(card.locator('input[autocomplete=nickname]')).toHaveValue('Bia')

    // Another writer assigns them on a vuln: the operator chip shows the display name.
    const other = await createUser(admin, 'write_all')
    const v = await newVuln(admin, { operator_ids: [user.id] })
    const ctx = await browser.newContext()
    const p2 = await ctx.newPage()
    await loginUI(p2, other.username, other.password)
    await p2.goto(`/vulnerabilities/${v.id}`)
    await expect(p2.getByText('Bia', { exact: true }).first()).toBeVisible()
    await expect(p2.getByText(user.username, { exact: true })).toHaveCount(0)
    await ctx.close()
    await cleanup(admin, { vulns: [v.id] })
  })

  test('the admin sees and edits names on the Users page', async ({ page }) => {
    const admin = await adminToken()
    const user = await createUser(admin, 'read_all')
    await loginUI(page, 'admin', 'admin')
    await page.goto(`/users?user=${user.id}`)
    const name = `Carlos Mendes ${tag()}`
    const full = page.locator('.detail .nameIn').first()
    await full.fill(name)
    await full.blur()
    await expect(page.locator('.detail .dName')).toHaveText(name)
    await page.locator('.toolbar .search').fill(name.split(' ')[2])
    await expect(page.locator('.utable tbody tr')).toHaveCount(1)
    await expect(page.locator('.utable tbody tr td').nth(1)).toHaveText(name)
  })
})
