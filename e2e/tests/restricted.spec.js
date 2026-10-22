import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, newReport, newVuln, tag } from '../support/api.js'
import { filterHub, loginUI, rowCount } from '../support/ui.js'

let admin
let rw // write_restricted
let rr // read_restricted
const vulns = []
const reports = []

test.beforeAll(async () => {
  admin = await adminToken()
  rw = await createUser(admin, 'write_restricted')
  rr = await createUser(admin, 'read_restricted')
})
test.afterAll(async () => cleanup(admin, { vulns, reports }))

const mk = async (fields, token = admin) => { const v = await newVuln(token, fields); vulns.push(v.id); return v }

test.describe('restricted roles', () => {
  test('a restricted writer creates records and sees only its own and the ones it operates', async ({ page }) => {
    const u = tag()
    const foreign = await mk({ identifier: `e2e-x-${u}-foreign` })
    const assigned = await mk({ identifier: `e2e-x-${u}-assigned`, operator_ids: [rw.id] })
    await loginUI(page, rw.username, rw.password)
    await expect(page.locator('.sidebar .navItem[aria-label^="Criar"]')).toHaveCount(2)

    // create one through the UI: the logged user is the default operator
    await page.click('.btn.primary:has-text("Criar")')
    await expect(page).toHaveURL(/vulnerabilities\/new/)
    await page.locator('.infoGrid input').first().fill(`e2e-x-${u}-own`)
    await page.click('.pageActions .btn.primary')
    await expect(page).toHaveURL(/vulnerabilities\/[0-9a-f-]{36}$/)
    vulns.push(page.url().split('/').pop())
    await page.goto('/hub')

    await filterHub(page, `e2e-x-${u}`)
    expect(await rowCount(page)).toBe(2)
    await expect(page.locator('.vtable tbody')).toContainText(`e2e-x-${u}-own`)
    await expect(page.locator('.vtable tbody')).toContainText(`e2e-x-${u}-assigned`)
    await expect(page.locator('.vtable tbody')).not.toContainText('foreign')

    // operating is enough to edit, not to delete
    await page.click(`.vtable tbody tr:has-text("${assigned.identifier}") td:nth-child(10) button`)
    await expect(page.locator('.rowMenuInline button')).toHaveText(['Visualizar', 'Detalhar', 'Exportar'])
    await page.click('.rowMenuInline button:has-text("Detalhar")')
    await expect(page.locator('.pageActions .btn.primary')).toBeVisible()
    await expect(page.locator('.pageActions .btn.danger')).toHaveCount(0)

    // a record it cannot read does not exist for it
    const res = await api(`/vulnerabilities/${foreign.id}`, { token: (await api('/auth/login', { body: { username: rw.username, password: rw.password } })).data.access_token })
    expect(res.status).toBe(404)
  })

  test('a restricted reader sees what is shared with it, and sharing takes effect at once', async ({ browser }) => {
    const u = tag()
    const shared = await mk({ identifier: `e2e-s-${u}-shared` })
    const hidden = await mk({ identifier: `e2e-s-${u}-hidden` })

    const writerPage = await (await browser.newContext()).newPage()
    await loginUI(writerPage, 'admin', 'admin')
    await writerPage.goto(`/vulnerabilities/${shared.id}`)
    await writerPage.locator('.f:has(label:text-is("Compartilhado com")) .opchip.plus').click()
    await writerPage.fill('.opsearch', rr.username)
    await writerPage.click(`.opitem:has-text("${rr.username}")`)
    await writerPage.click('.pageActions .btn.primary')
    await expect(writerPage.locator('.f:has(label:text-is("Compartilhado com")) .opchip.on')).toHaveText(rr.username)

    const readerPage = await (await browser.newContext()).newPage()
    await loginUI(readerPage, rr.username, rr.password)
    await filterHub(readerPage, `e2e-s-${u}`)
    expect(await rowCount(readerPage)).toBe(1)
    await expect(readerPage.locator('.vtable tbody')).toContainText('shared')
    await expect(readerPage.locator('.btn.primary:has-text("Criar")')).toHaveCount(0)
    await expect(readerPage.locator('.sidebar .navItem[aria-label^="Criar"]')).toHaveCount(0)

    await readerPage.click('.vtable tbody tr:first-child td:nth-child(2)')
    await readerPage.click('.details .btn:has-text("Detalhar")')
    await expect(readerPage.locator('.pageActions .btn.primary, .pageActions .btn.danger')).toHaveCount(0)
    await expect(readerPage.locator('.infoGrid input, .mdEditor')).toHaveCount(0)
    await expect(readerPage.locator('.infoGrid .roVal').first()).toContainText('shared')
    // the sharing list is read-only for a reader: its entry shows, no "+"
    await expect(readerPage.locator('.opchip.plus')).toHaveCount(0)
    void hidden
  })

  test('admins can give the restricted roles from the users screen', async ({ page }) => {
    await loginUI(page, 'admin', 'admin')
    await page.locator('.sidebar .navItem[aria-label="Usuários"]').click()
    await expect(page.locator('.pageTop .btn.primary')).toBeVisible()
    await page.click('.pageTop .btn.primary')
    const options = await page.locator('.formRow select option').allTextContents()
    expect(options).toEqual(expect.arrayContaining(['Editor restrito', 'Leitor restrito']))
  })

  test('reports: restricted users see only theirs / shared ones', async ({ page }) => {
    const u = tag()
    const shared = await newReport(admin, { name: `e2e-rs-${u}-shared`, viewer_ids: [rr.id] })
    const hidden = await newReport(admin, { name: `e2e-rs-${u}-hidden` })
    reports.push(shared.id, hidden.id)
    await loginUI(page, rr.username, rr.password)
    await page.click('.tab:has-text("Relatórios")')
    await filterHub(page, `e2e-rs-${u}`)
    expect(await rowCount(page, '.rtable')).toBe(1)
    await expect(page.locator('.rtable tbody')).toContainText('shared')
    await page.goto(`/reports/${shared.id}`)
    await expect(page.locator('.pageActions .btn.danger')).toHaveCount(0)
    await expect(page.locator('.grid4 input, .mdEditor')).toHaveCount(0)
    await expect(page.locator('.grid4 .roVal').first()).toContainText('shared')
  })
})
