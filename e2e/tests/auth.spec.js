import { expect, test } from '@playwright/test'
import { adminToken, createUser } from '../support/api.js'
import { loginUI } from '../support/ui.js'

test.describe('authentication', () => {
  test('a wrong password shows an error and stays on the login page', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[autocomplete=username]', 'admin')
    await page.fill('input[type=password]', 'definitely-wrong')
    await page.click('button')
    await expect(page.locator('.error')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('visiting a protected page while signed out goes to the login page', async ({ page }) => {
    await page.goto('/hub')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('the first login forces a password change before anything else', async ({ page }) => {
    const admin = await adminToken()
    const user = await createUser(admin, 'writer_all', { finishFirstLogin: false })

    await page.goto('/login')
    await page.fill('input[autocomplete=username]', user.username)
    await page.fill('input[type=password]', user.password)
    await page.click('button')

    await expect(page).toHaveURL(/\/profile$/)
    await expect(page.locator('.banner')).toContainText('nova senha')
    await expect(page.locator('.sidebar')).toHaveClass(/locked/)

    // typing another address cannot get around it
    await page.goto('/hub')
    await expect(page).toHaveURL(/\/profile$/)

    const [current, next, confirm] = await page.locator('input[type=password]').all()
    const submit = page.locator('.pwCard button.primary')

    await current.fill(user.password)
    await next.fill('short')
    await expect(page.locator('.pwCard .err')).toContainText('8')
    await next.fill(user.password)
    await expect(page.locator('.pwCard .err')).toBeVisible()           // same as the current one
    await next.fill('Brand-New-9')
    await confirm.fill('Different-1')
    await expect(submit).toBeDisabled()                                // confirmation mismatch

    await current.fill('wrong-current')
    await confirm.fill('Brand-New-9')
    await submit.click()
    await expect(page.locator('.pwCard .err')).toContainText('incorreta')   // the server's verdict
    await expect(page).toHaveURL(/\/profile$/)

    await current.fill(user.password)
    await submit.click()
    await expect(page).toHaveURL(/\/hub/)
    await expect(page.locator('.vtable')).toBeVisible()
    await expect(page.locator('.sidebar')).not.toHaveClass(/locked/)
  })

  test('an expired access token is refreshed without the user noticing', async ({ page }) => {
    const admin = await adminToken()
    const user = await createUser(admin, 'writer_all')
    await loginUI(page, user.username, user.password)

    await page.evaluate(() => localStorage.setItem('rtp_access', 'not.a.valid.jwt'))
    await page.reload()
    await expect(page.locator('.vtable')).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('rtp_access'))).not.toBe('not.a.valid.jwt')
  })

  test('when the refresh token is dead the user is sent back to login', async ({ page }) => {
    const admin = await adminToken()
    const user = await createUser(admin, 'writer_all')
    await loginUI(page, user.username, user.password)

    await page.evaluate(() => { localStorage.setItem('rtp_access', 'bad'); localStorage.setItem('rtp_refresh', 'bad') })
    await page.reload()
    await expect(page).toHaveURL(/\/login$/)
    expect(await page.evaluate(() => localStorage.getItem('rtp_access'))).toBeNull()
  })

  test('the profile menu offers language, profile and sign out', async ({ page }) => {
    const admin = await adminToken()
    const user = await createUser(admin, 'writer_all')
    await loginUI(page, user.username, user.password)

    await page.click('.profileBtn')
    await expect(page.locator('.profileMenu .menuItem')).toHaveText(['Português (BR)', 'English', 'Perfil', 'Sair'])

    // language switches the UI, survives a reload, and the menu closes by itself
    await page.click('.menuItem:has-text("English")')
    await expect(page.locator('.profileMenu')).toHaveCount(0)
    await expect(page.locator('h1')).toHaveText('Operations Hub')
    await page.reload()
    await expect(page.locator('h1')).toHaveText('Operations Hub')
    await page.click('.profileBtn')
    await page.click('.menuItem:has-text("Português")')

    // profile page
    await page.click('.profileBtn')
    await page.click('.menuItem:has-text("Perfil")')
    await expect(page).toHaveURL(/\/profile$/)
    await expect(page.locator('.banner')).toHaveCount(0)               // not forced any more

    // clicking elsewhere closes the menu; sign out ends the session
    await page.click('.profileBtn')
    await page.click('h1')
    await expect(page.locator('.profileMenu')).toHaveCount(0)
    await page.click('.profileBtn')
    await page.click('.menuItem:has-text("Sair")')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('read-only roles do not see write navigation', async ({ page }) => {
    const admin = await adminToken()
    const reader = await createUser(admin, 'reader_all')
    await loginUI(page, reader.username, reader.password)
    const labels = await page.locator('.sidebar .navItem').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')))
    expect(labels).not.toContain('Usuários')
    expect(labels).not.toContain('Chaves de API')
    expect(labels).not.toContain('Logs de Auditoria')
    await page.goto('/users')                       // and the router refuses direct access
    await expect(page).toHaveURL(/\/hub/)
  })
})
