import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, newReport, tag } from '../support/api.js'
import { answerDialog, loginUI } from '../support/ui.js'

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

const tokenOf = async (u) => (await api('/auth/login', { body: { username: u.username, password: u.password } })).data.access_token
const newTemplate = async (token, body) => (await api('/report-templates', { token, body })).data
const sharing = (token, id, action) => api(`/report-templates/${id}/sharing`, { token, body: { action } })
async function sharedTemplate(ownerTok, body) {
  const t = await newTemplate(ownerTok, body)
  await sharing(ownerTok, t.id, 'request')
  await sharing(admin, t.id, 'approve')
  return t
}
const newPage = async (browser, user) => {
  const page = await (await browser.newContext()).newPage()
  await loginUI(page, user.username, user.password)
  return page
}

async function sourceReport(token, u) {
  const r = await newReport(token, { name: `e2e-tplsrc-${u}` })
  reports.push(r.id)
  await api(`/reports/${r.id}`, { token, method: 'PATCH', body: { introduction_md: `Intro do template ${u}` } })
  await api(`/reports/${r.id}/sections`, { token, body: { title: 'Metodologia', content_markdown: `Método ${u}` } })
  return r
}

async function saveAsTemplate(page, name) {
  await page.click('.pageActions button:has-text("Salvar como Template")')
  const modal = page.locator('.modal')
  await expect(modal).toBeVisible()
  await expect(modal.locator('input[type=checkbox]')).toHaveCount(0)             // nobody shares directly
  await modal.locator('input').fill(name)
  await modal.locator('.btn.primary').click()
  await expect(modal).toHaveCount(0)
  await expect(page.locator('.ok.msg')).toContainText(name)
}

test.describe('report templates', () => {
  test('save a report as a template, then start a new report from it', async ({ page }) => {
    const u = tag()
    const src = await sourceReport(await tokenOf(writer), u)
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/reports/${src.id}`)
    await saveAsTemplate(page, `e2e-tpl-${u}`)

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
    await newTemplate(await tokenOf(writer), {
      name: `e2e-tplpage-${u}`, introduction_md: `**Intro** ${u}`,
      sections: [{ title: 'Metodologia', content_markdown: 'OWASP' }],
    })
    await loginUI(page, writer.username, writer.password)
    await page.locator('.sidebar .navItem[aria-label="Templates"]').click()
    await expect(page).toHaveURL(/\/templates$/)
    await page.fill('.search', `e2e-tplpage-${u}`)
    const row = page.locator('.ttable tbody tr').first()
    await expect(row).toContainText('Você')
    await expect(row.locator('.pill')).toHaveText('Privado')
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

  test('sharing: the owner asks, an admin approves, then everyone has it and the owner cannot change it', async ({ browser }) => {
    const u = tag()
    const t = await newTemplate(await tokenOf(writer), { name: `e2e-tplshare-${u}`, introduction_md: 'x' })

    // the owner asks (and is warned that it becomes read-only for them)
    const owner = await newPage(browser, writer)
    await owner.goto(`/templates?template=${t.id}`)
    const od = owner.locator('.detail')
    await expect(od.locator('.shareActs .btn')).toHaveText(['Solicitar compartilhamento'])
    await od.locator('.shareActs .btn').click()
    expect(await answerDialog(owner, 'Confirmar')).toContain('não poderá mais editar')
    await expect(owner.locator('.ok.msg')).toContainText('precisa aprovar')
    await expect(od.locator('.facts .pill')).toHaveText('Aguardando aprovação')
    await expect(od.locator('.btn:has-text("Editar"), .btn:has-text("Excluir")')).toHaveCount(0)   // frozen
    await expect(od.locator('.shareActs .btn')).toHaveText(['Cancelar solicitação'])

    // not shared yet: another user does not see it
    const otherTok = await tokenOf(other)
    expect((await api('/report-templates', { token: otherTok })).data.some((x) => x.id === t.id)).toBe(false)

    // the admin finds it in the queue and approves it
    const adm = await newPage(browser, { username: 'admin', password: 'admin' })
    await adm.goto('/templates')
    await adm.click('.toolbar .queue')
    await expect(adm.locator(`.ttable tbody tr:has-text("e2e-tplshare-${u}")`)).toHaveCount(1)
    await adm.click(`.ttable tbody tr:has-text("e2e-tplshare-${u}")`)
    await expect(adm.locator('.detail .shareActs .btn')).toHaveText(['Recusar', 'Aprovar'])
    await adm.click('.detail .shareActs .btn:has-text("Aprovar")')
    await expect(adm.locator('.detail .facts .pill')).toHaveText('Compartilhado')
    await expect(adm.locator('.detail .facts')).toContainText('admin')                 // who decided

    // everyone has it now; its owner can no longer edit or delete it
    await owner.reload()
    await expect(od.locator('.facts .pill')).toHaveText('Compartilhado')
    await expect(od.locator('.btn:has-text("Editar"), .btn:has-text("Excluir"), .shareActs .btn')).toHaveCount(0)
    const o2 = await newPage(browser, other)
    await o2.goto('/reports/new')
    await o2.click('.tplPicker .opchip')
    await expect(o2.locator('.tplMenu')).toContainText(`e2e-tplshare-${u}`)
  })

  test('an admin can reject a request: the template goes back to its owner, private', async ({ browser }) => {
    const u = tag()
    const tok = await tokenOf(writer)
    const t = await newTemplate(tok, { name: `e2e-tplrej-${u}` })
    await sharing(tok, t.id, 'request')
    const adm = await newPage(browser, { username: 'admin', password: 'admin' })
    await adm.goto(`/templates?template=${t.id}`)
    await adm.click('.detail .shareActs .btn:has-text("Recusar")')
    await expect(adm.locator('.ok.msg')).toContainText('recusada')
    const owner = await newPage(browser, writer)
    await owner.goto(`/templates?template=${t.id}`)
    await expect(owner.locator('.detail .facts .pill')).toHaveText('Privado')
    await expect(owner.locator('.detail .btn:has-text("Editar")')).toBeVisible()
  })

  test('an admin can unshare a template: nobody can use it, its owner included, until it is shared again', async ({ browser }) => {
    const u = tag()
    const t = await sharedTemplate(await tokenOf(writer), { name: `e2e-tplunsh-${u}` })
    const adm = await newPage(browser, { username: 'admin', password: 'admin' })
    await adm.goto(`/templates?template=${t.id}`)
    await adm.click('.detail .shareActs .btn:has-text("Remover compartilhamento")')
    await answerDialog(adm, 'Confirmar')
    await expect(adm.locator('.detail .facts .pill')).toHaveText('Indisponível')
    await expect(adm.locator('.detail .shareActs .btn')).toHaveText(['Compartilhar novamente'])

    for (const user of [writer, other]) {                                          // owner included
      const p = await newPage(browser, user)
      await p.goto('/templates')
      await expect(p.locator(`.ttable tbody tr:has-text("e2e-tplunsh-${u}")`)).toHaveCount(0)
      await p.goto('/reports/new')
      await p.click('.tplPicker .opchip')
      await expect(p.locator('.tplMenu')).not.toContainText(`e2e-tplunsh-${u}`)
    }
    await adm.goto('/reports/new')                                                  // not even the admin uses it
    await adm.click('.tplPicker .opchip')
    await expect(adm.locator('.tplMenu')).not.toContainText(`e2e-tplunsh-${u}`)

    await adm.goto(`/templates?template=${t.id}`)
    await adm.click('.detail .shareActs .btn:has-text("Compartilhar novamente")')
    await expect(adm.locator('.detail .facts .pill')).toHaveText('Compartilhado')
  })

  test('the owner edits a private template; leaving with unsaved edits asks first', async ({ page }) => {
    const u = tag()
    const t = await newTemplate(await tokenOf(writer), { name: `e2e-tpledit-${u}`, introduction_md: 'antes' })
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/templates?template=${t.id}`)
    const detail = page.locator('.detail')
    await detail.locator('.btn:has-text("Editar")').click()

    await detail.locator('.nameInput').fill(`e2e-tpledit-${u}-v2`)
    await detail.locator('.mdEditor textarea').nth(1).fill('depois')
    await detail.locator('.addSection').click()
    await detail.locator('.extraHead input').fill('Nova seção')

    // trying to switch template with unsaved edits asks; saying no keeps the editor
    await page.locator('.ttable tbody tr').first().click()
    expect(await answerDialog(page, 'Cancelar')).toContain('alterações')
    await expect(detail.locator('.nameInput')).toBeVisible()

    await detail.locator('.btn.primary:has-text("Salvar")').click()
    await expect(page.locator('.ok.msg')).toContainText(`e2e-tpledit-${u}-v2`)
    await expect(detail.locator('.dName')).toHaveText(`e2e-tpledit-${u}-v2`)
    await expect(detail.locator('.block:has(h3:text-is("Introdução")) .mdView')).toHaveText('depois')
    await expect(detail.locator('.extraTitle')).toHaveText('Nova seção')
  })

  test('the owner deletes a private template', async ({ page }) => {
    const u = tag()
    const t = await newTemplate(await tokenOf(writer), { name: `e2e-tpldel-${u}` })
    await loginUI(page, writer.username, writer.password)
    await page.goto(`/templates?template=${t.id}`)
    await page.locator('.detail .btn.danger:has-text("Excluir")').click()
    await answerDialog(page, 'Excluir')
    await expect(page.locator('.ok.msg')).toContainText(`e2e-tpldel-${u}`)
    await expect(page).toHaveURL(/\/templates$/)
    await expect(page.locator(`.ttable tbody tr:has-text("e2e-tpldel-${u}")`)).toHaveCount(0)
  })
})
