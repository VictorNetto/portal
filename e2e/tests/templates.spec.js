import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, newReport, tag } from '../support/api.js'
import { loginUI } from '../support/ui.js'

let admin
let writer
let other
const reports = []

test.beforeAll(async () => {
  admin = await adminToken()
  writer = await createUser(admin, 'write_all')
  other = await createUser(admin, 'write_all')
})
test.afterAll(async () => cleanup(admin, { reports }))

async function sourceReport(token, u) {
  const r = await newReport(token, { name: `e2e-tplsrc-${u}` })
  reports.push(r.id)
  await api(`/reports/${r.id}`, { token, method: 'PATCH', body: { introduction_md: `Intro do template ${u}` } })
  await api(`/reports/${r.id}/sections`, { token, body: { title: 'Metodologia', content_markdown: `Método ${u}` } })
  return r
}

async function saveAsTemplate(page, name, { forAll = false, adminOnlyHidden = false } = {}) {
  await page.click('.pageActions button:has-text("Salvar como Template")')
  const modal = page.locator('.modal')
  await expect(modal).toBeVisible()
  if (adminOnlyHidden) await expect(modal.locator('input[type=checkbox]')).toHaveCount(0)   // 'for all users' is admin-only
  await modal.locator('input:not([type=checkbox])').fill(name)
  if (forAll) await modal.locator('input[type=checkbox]').check()
  await modal.locator('.btn.primary').click()
  await expect(modal).toHaveCount(0)
  await expect(page.locator('.ok.msg')).toContainText(name)
}

test.describe('report templates', () => {
  test('save a report as a template, then start a new report from it', async ({ page }) => {
    const u = tag()
    const writerTok = (await api('/auth/login', { body: { username: writer.username, password: writer.password } })).data.access_token
    const src = await sourceReport(writerTok, u)
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/reports/${src.id}`)
    await saveAsTemplate(page, `e2e-tpl-${u}`, { adminOnlyHidden: true })

    await page.goto('/reports/new')
    const chip = page.locator('.tplPicker .opchip')
    await expect(chip).toHaveText('Nenhum')
    await chip.click()
    await expect(page.locator('.tplMenu .tplGroup').first()).toHaveText('Meus templates')
    await page.click(`.tplMenu .tplItem:has-text("e2e-tpl-${u}")`)
    await expect(chip).toHaveText(`e2e-tpl-${u}`)

    await page.locator('.createCard input').first().fill(`e2e-tplnew-${u}`)
    await page.click('.createCard .btn.primary')
    await expect(page).toHaveURL(/\/reports\/[0-9a-f-]{36}$/)
    reports.push(page.url().split('/').pop())
    await expect(page.locator('.mdEditor textarea').nth(1)).toHaveValue(`Intro do template ${u}`)
    await expect(page.locator('.extraHead input').first()).toHaveValue('Metodologia')
  })

  test('templates are private; an admin can make one available to everyone', async ({ browser }) => {
    const u = tag()
    const src = await sourceReport(admin, u)

    const adminPage = await (await browser.newContext()).newPage()
    await loginUI(adminPage, 'admin', 'admin')
    await adminPage.goto(`/reports/${src.id}`)
    await saveAsTemplate(adminPage, `e2e-tplall-${u}`, { forAll: true })
    await saveAsTemplate(adminPage, `e2e-tplmine-${u}`)

    const otherPage = await (await browser.newContext()).newPage()
    await loginUI(otherPage, other.username, other.password)
    await otherPage.goto('/reports/new')
    await otherPage.click('.tplPicker .opchip')
    const menu = otherPage.locator('.tplMenu')
    await expect(menu).toContainText('Para todos os usuários')
    await expect(menu).toContainText(`e2e-tplall-${u}`)
    await expect(menu).not.toContainText(`e2e-tplmine-${u}`)
  })
})
