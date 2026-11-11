import { expect, test } from '@playwright/test'
import { adminToken, cleanup, createUser, login, newVuln, tag } from '../support/api.js'
import { filterHub, loginUI, rowCount } from '../support/ui.js'

let admin
let writer
const vulns = []

test.beforeAll(async () => {
  admin = await adminToken()
  writer = await createUser(admin, 'write_all')
})
test.afterAll(async () => cleanup(admin, { vulns }))

const menu = (page) => page.locator('.filterbar .menu li')

test.describe('filter menu', () => {
  test('"/" lists the basic keys; "Mais filtros…" adds the advanced ones', async ({ page }) => {
    await loginUI(page, writer.username, writer.password)
    const input = page.locator('.filterbar input')
    await input.fill('/')
    await expect(menu(page)).toHaveText(['status', 'cvss', 'report', 'operator', 'Mais filtros…'])

    await menu(page).filter({ hasText: 'Mais filtros…' }).click()
    await expect(menu(page)).toHaveText([
      'status', 'cvss', 'report', 'operator',
      'source', 'created', 'updated', 'sent', 'accepted', 'fixing', 'retesting', 'fixed', 'risk',
    ])
    await expect(input).toHaveValue('/')                         // the text is untouched
    await expect(menu(page).nth(4)).toHaveClass(/active/)        // the keyboard lands on the first new one

    // A date key offers quick periods, and completes the token.
    await menu(page).filter({ hasText: /^created$/ }).click()
    await expect(input).toHaveValue('created:')
    await expect(menu(page)).toHaveText(['1d', '7d', '30d', '90d', '1y'])
    await menu(page).filter({ hasText: '7d' }).click()
    await expect(input).toHaveValue('created:7d')

    // The next "/" starts short again.
    await input.fill('created:7d /')
    await expect(menu(page).last()).toHaveText('Mais filtros…')

    // Typing finds advanced keys without the extra step; the id key is gone.
    await input.fill('/fi')
    await expect(menu(page)).toHaveText(['fixing', 'fixed'])
    await input.fill('/id')
    await expect(menu(page)).toHaveCount(0)
  })

  test('keyboard: Enter on "Mais filtros…" expands, Enter again picks the key', async ({ page }) => {
    await loginUI(page, writer.username, writer.password)
    const input = page.locator('.filterbar input')
    await input.fill('/')
    for (let i = 0; i < 4; i++) await input.press('ArrowDown')
    await expect(menu(page).nth(4)).toHaveClass(/active/)
    await input.press('Enter')
    await expect(menu(page).nth(4)).toHaveText('source')
    await input.press('ArrowDown')
    await input.press('Enter')
    await expect(input).toHaveValue('created:')
  })
})

test.describe('date filters', () => {
  test('created:1d keeps what was made today, -created:1d hides it', async ({ page }) => {
    const u = tag()
    const v = await newVuln(await login(writer.username, writer.password), { identifier: `e2e-date-${u}` })
    vulns.push(v.id)
    await loginUI(page, writer.username, writer.password)

    await filterHub(page, `e2e-date-${u} created:1d`)
    expect(await rowCount(page)).toBe(1)
    await filterHub(page, `e2e-date-${u} -created:1d`)
    expect(await rowCount(page)).toBe(0)
    // Explicit dates, d1.d2.d3 in Brazilian order.
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const day = `${pad(now.getDate())}-${pad(now.getMonth() + 1)}-${now.getFullYear()}`
    const month = `${pad(now.getMonth() + 1)}-${now.getFullYear()}`
    const cases = {
      '01-2020..12-2020': 0,                    // a range that ended long ago
      [`${now.getFullYear() - 1}..${now.getFullYear()}`]: 1,
      [month]: 1,                               // a single date: within it
      [`.${day}.`]: 1,                          // d2 only: the same
      [`${day}..`]: 1,                          // today or later
      [`..${now.getFullYear() - 1}`]: 0,        // last year or earlier
      '1y': 1,
      '31-02-2026': 1,                          // not a date: the filter is ignored
    }
    for (const [when, n] of Object.entries(cases)) {
      await filterHub(page, `e2e-date-${u} created:${when}`)
      expect(await rowCount(page), when).toBe(n)
    }
    // Never sent, so no sent date: sent:30d excludes it, -sent:30d keeps it.
    await filterHub(page, `e2e-date-${u} sent:30d`)
    expect(await rowCount(page)).toBe(0)
    await filterHub(page, `e2e-date-${u} -sent:30d`)
    expect(await rowCount(page)).toBe(1)
  })

  test('the defense team gets the short menu with its own dates', async ({ page }) => {
    const defense = await createUser(admin, 'defense')
    await page.goto('/login')
    await page.fill('input[autocomplete=username]', defense.username)
    await page.fill('input[type=password]', defense.password)
    await page.click('button')
    await expect(page).toHaveURL(/\/defense\/new$/)

    const input = page.locator('.filterbar input')
    await input.fill('/')
    await expect(menu(page)).toHaveText(['status', 'cvss', 'report', 'Mais filtros…'])
    await menu(page).filter({ hasText: 'Mais filtros…' }).click()
    await expect(menu(page)).toHaveText(['status', 'cvss', 'report', 'sent', 'accepted', 'fixing', 'retesting', 'fixed', 'risk'])
  })
})
