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

  test('the Templates page lists them and shows what each contains', async ({ page }) => {
    const u = tag()
    const writerTok = (await api('/auth/login', { body: { username: writer.username, password: writer.password } })).data.access_token
    await api('/report-templates', { token: writerTok, body: {
      name: `e2e-tplpage-${u}`, introduction_md: `**Intro** ${u}`,
      sections: [{ title: 'Metodologia', content_markdown: 'OWASP' }],
    } })
    await loginUI(page, writer.username, writer.password)
    await page.locator('.sidebar .navItem[aria-label="Templates"]').click()
    await expect(page).toHaveURL(/\/templates$/)
    await page.fill('.search', `e2e-tplpage-${u}`)
    const row = page.locator('.ttable tbody tr').first()
    await expect(row).toContainText('Você')
    await expect(row).toContainText('Somente o dono')
    await row.click()
    await expect(page).toHaveURL(/template=/)
    const detail = page.locator('.detail')
    await expect(detail.locator('.dName')).toHaveText(`e2e-tplpage-${u}`)
    await expect(detail.locator('.mdView strong').first()).toHaveText('Intro')         // rendered, not raw Markdown
    await expect(detail.locator('.extraTitle')).toHaveText('Metodologia')
  })

  test('readers have no Templates page', async ({ page }) => {
    const reader = await createUser(admin, 'read_all')
    await loginUI(page, reader.username, reader.password)
    await expect(page.locator('.sidebar .navItem[aria-label="Templates"]')).toHaveCount(0)
    await page.goto('/templates')
    await expect(page).toHaveURL(/\/hub/)
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

  test('the owner edits a private template; leaving with unsaved edits asks first', async ({ page }) => {
    const u = tag()
    const tok = (await api('/auth/login', { body: { username: writer.username, password: writer.password } })).data.access_token
    const tpl = (await api('/report-templates', { token: tok, body: { name: `e2e-tpledit-${u}`, introduction_md: 'antes' } })).data
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/templates?template=${tpl.id}`)
    const detail = page.locator('.detail')
    await detail.locator('.btn:has-text("Editar")').click()

    await detail.locator('.nameInput').fill(`e2e-tpledit-${u}-v2`)
    await detail.locator('.mdEditor textarea').nth(1).fill('depois')
    await detail.locator('.addSection').click()
    await detail.locator('.extraHead input').fill('Nova seção')

    // trying to close with unsaved edits asks; saying no keeps the editor
    const dialogs = []
    page.once('dialog', (d) => { dialogs.push(d.message()); d.dismiss() })
    await page.locator('.ttable tbody tr').first().click()
    await expect.poll(() => dialogs.length).toBe(1)
    await expect(detail.locator('.nameInput')).toBeVisible()

    await detail.locator('.btn.primary:has-text("Salvar")').click()
    await expect(page.locator('.ok.msg')).toContainText(`e2e-tpledit-${u}-v2`)
    await expect(detail.locator('.dName')).toHaveText(`e2e-tpledit-${u}-v2`)
    await expect(detail.locator('.block:has(h3:text-is("Introdução")) .mdView')).toHaveText('depois')
    await expect(detail.locator('.extraTitle')).toHaveText('Nova seção')
    await expect(page.locator(`.ttable tbody tr:has-text("e2e-tpledit-${u}-v2")`)).toHaveCount(1)
  })

  test('the owner deletes a private template', async ({ page }) => {
    const u = tag()
    const tok = (await api('/auth/login', { body: { username: writer.username, password: writer.password } })).data.access_token
    const tpl = (await api('/report-templates', { token: tok, body: { name: `e2e-tpldel-${u}` } })).data
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/templates?template=${tpl.id}`)
    page.once('dialog', (d) => d.accept())
    await page.locator('.detail .btn.danger:has-text("Excluir")').click()
    await expect(page.locator('.ok.msg')).toContainText(`e2e-tpldel-${u}`)
    await expect(page).toHaveURL(/\/templates$/)
    await expect(page.locator(`.ttable tbody tr:has-text("e2e-tpldel-${u}")`)).toHaveCount(0)
  })

  test('once shared with everyone, only an admin may edit or delete it', async ({ browser }) => {
    const u = tag()
    const tok = (await api('/auth/login', { body: { username: writer.username, password: writer.password } })).data.access_token
    const tpl = (await api('/report-templates', { token: tok, body: { name: `e2e-tplshared-${u}` } })).data
    await api(`/report-templates/${tpl.id}`, { token: admin, method: 'PATCH', body: { is_global: true } })

    const owner = await (await browser.newContext()).newPage()
    await loginUI(owner, writer.username, writer.password)
    await owner.goto(`/templates?template=${tpl.id}`)
    await expect(owner.locator('.detail .dName')).toHaveText(`e2e-tplshared-${u}`)
    await expect(owner.locator('.detail .btn:has-text("Editar"), .detail .btn:has-text("Excluir")')).toHaveCount(0)

    const adm = await (await browser.newContext()).newPage()
    await loginUI(adm, 'admin', 'admin')
    await adm.goto(`/templates?template=${tpl.id}`)
    await expect(adm.locator('.detail .btn:has-text("Editar")')).toBeVisible()
    await expect(adm.locator('.detail .btn:has-text("Excluir")')).toBeVisible()
  })
})
