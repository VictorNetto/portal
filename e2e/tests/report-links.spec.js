import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, login, newReport, newVuln, savedVuln, tag } from '../support/api.js'
import { autoDialogs, collectPageErrors, loginUI } from '../support/ui.js'

let admin
let alice
const reports = []
const vulns = []

test.beforeAll(async () => {
  admin = await adminToken()
  alice = await createUser(admin, 'write_all')
  alice.token = await login(alice.username, alice.password)
})
test.afterAll(async () => cleanup(admin, { reports, vulns }))

test.describe('linking vulnerabilities to a report', () => {
  test('link existing vulnerabilities, then unlink one', async ({ page }) => {
    const errors = collectPageErrors(page)
    autoDialogs(page)
    const u = tag()
    const report = await newReport(alice.token, { name: `e2e-link-${u}` })
    reports.push(report.id)
    const draft = await newVuln(alice.token, { identifier: `e2e-link-${u}-draft` })
    const ready = await savedVuln(alice.token, { identifier: `e2e-link-${u}-ready` })
    vulns.push(draft.id, ready.id)

    await loginUI(page, alice.username, alice.password)
    await page.goto(`/reports/${report.id}`)
    await expect(page.locator('.banner.mine')).toBeVisible()

    // the picker lists standalone vulns not sent yet; the search narrows it
    await page.getByRole('button', { name: 'Vincular', exact: true }).click()
    const modal = page.locator('.linkModal')
    await modal.locator('.linkSearch').fill(`e2e-link-${u}`)
    await expect(modal.locator('.linkList li')).toHaveCount(2)
    await modal.locator('label', { hasText: `${u}-draft` }).locator('input').check()
    await modal.locator('label', { hasText: `${u}-ready` }).locator('input').check()
    await modal.getByRole('button', { name: 'Vincular (2)' }).click()
    await expect(modal).toBeHidden()

    const rows = page.locator('.vt tbody tr')
    await expect(rows).toHaveCount(2)
    await expect(page.locator('.vt tbody tr', { hasText: `${u}-ready` }).locator('.pill')).toHaveText('Rascunho')

    // unlink: it becomes a standalone draft again
    await page.locator('.vt tbody tr', { hasText: `${u}-draft` }).getByRole('button', { name: 'Desvincular' }).click()
    await expect(rows).toHaveCount(1)
    const back = await api(`/vulnerabilities/${draft.id}`, { token: alice.token })
    expect(back.data.report_id).toBeNull()
    expect(errors).toEqual([])
  })

  test('without the lock there is nothing to link or unlink', async ({ page }) => {
    const report = await newReport(alice.token, { name: `e2e-link-${tag()}` })
    reports.push(report.id)
    await api(`/reports/${report.id}/lock`, { token: alice.token, method: 'DELETE' })
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/reports/${report.id}`)
    await expect(page.locator('.pageActions .btn.primary', { hasText: 'Editar' })).toBeVisible()   // free: offered to take the lock
    await expect(page.getByRole('button', { name: 'Vincular', exact: true })).toHaveCount(0)
  })
})

test.describe('long texts', () => {
  test('an editor expands to the window and collapses again; the notes expand too', async ({ page }) => {
    const v = await newVuln(alice.token, { identifier: `e2e-expand-${tag()}` })
    vulns.push(v.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    const editor = page.locator('.mdEditor').first()
    const area = editor.locator('textarea')
    const before = (await area.boundingBox()).height
    await editor.getByRole('button', { name: 'Expandir' }).click()
    await expect.poll(async () => (await area.boundingBox()).height).toBeGreaterThan(before + 200)
    if (process.env.E2E_SHOTS) { await page.waitForTimeout(800); await page.screenshot({ path: `${process.env.E2E_SHOTS}/editor-expanded.png` }) }
    await area.press('Escape')
    await expect.poll(async () => (await area.boundingBox()).height).toBe(before)
    // description, finding details, mitigation and the internal notes (now at the end of the left column)
    await expect(page.getByRole('button', { name: 'Expandir' })).toHaveCount(4)
  })

  test('mitigation can be left blank when completing', async ({ page }) => {
    autoDialogs(page)
    const v = await newVuln(alice.token, { identifier: `e2e-nomit-${tag()}`, mitigation: '' })
    vulns.push(v.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    await expect(page.locator('.secTitle', { hasText: 'Mitigação' })).toHaveText('Mitigação / Solução')   // no asterisk
    await expect(page.locator('.secTitle', { hasText: 'Descrição' })).toHaveText('Descrição *')
    await page.getByRole('button', { name: 'Concluir' }).click()
    await expect.poll(async () => (await api(`/vulnerabilities/${v.id}`, { token: alice.token })).data.status).toBe('ready')
  })
})

test.describe('page layout', () => {
  test('the right column scrolls on its own and ends with the references', async ({ page }) => {
    const long = Array.from({ length: 80 }, (_, i) => `linha ${i + 1}`).join('\n')
    const refs = Array.from({ length: 40 }, (_, i) => `https://owasp.org/ref-${i + 1}`)
    const v = await newVuln(alice.token, { identifier: `e2e-cols-${tag()}`, finding_detail: long, references: refs })
    vulns.push(v.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    const side = page.locator('.side')
    await expect(side.locator('> section').last().locator('.secTitle')).toHaveText('Referências')
    await expect(page.locator('.layout > .stack').first().locator('> section').last().locator('.secTitle')).toHaveText('Notas Internas')

    const state = () => page.evaluate(() => {
      const m = document.querySelector('.main'); const s = document.querySelector('.side')
      return { main: m.scrollTop, side: s.scrollTop, sideTop: s.getBoundingClientRect().top,
        sideBottom: s.getBoundingClientRect().bottom, headerBottom: document.querySelector('.stickyTop').getBoundingClientRect().bottom,
        scrolls: s.scrollHeight > s.clientHeight }
    })
    // Scrolling the page leaves the right column in view, under the header.
    await page.evaluate(() => { document.querySelector('.main').scrollTop = 99999 })
    let s = await state()
    expect(s.main).toBeGreaterThan(0)
    expect(s.scrolls).toBe(true)
    expect(s.sideTop).toBeGreaterThanOrEqual(s.headerBottom)
    expect(s.sideBottom).toBeLessThanOrEqual(1000)
    if (process.env.E2E_SHOTS) await page.screenshot({ path: `${process.env.E2E_SHOTS}/side-column.png` })
    // Scrolling the right column does not move the page.
    await side.hover()
    await page.mouse.wheel(0, 600)
    await expect.poll(async () => (await state()).side).toBeGreaterThan(0)
    expect((await state()).main).toBe(s.main)
  })
})

test.describe('sections in the documents', () => {
  test('a vulnerability section can be left out of the documents', async ({ page }) => {
    const v = await newVuln(alice.token, { identifier: `e2e-doc-${tag()}` })
    vulns.push(v.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/vulnerabilities/${v.id}`)
    const card = page.locator('section', { has: page.locator('.secTitle', { hasText: 'Mitigação' }) })
    await card.getByLabel('No documento').uncheck()
    await expect(card).toHaveClass(/offDoc/)
    if (process.env.E2E_SHOTS) await page.screenshot({ path: `${process.env.E2E_SHOTS}/export-toggle.png` })
    await page.getByRole('button', { name: 'Salvar rascunho' }).click()
    await expect.poll(async () => (await api(`/vulnerabilities/${v.id}`, { token: alice.token })).data.export_hidden).toEqual(['mitigation'])
  })

  test('report sections can be left out of the documents, and read-only pages say so', async ({ page }) => {
    const report = await newReport(alice.token, { name: `e2e-doc-${tag()}` })
    reports.push(report.id)
    await loginUI(page, alice.username, alice.password)
    await page.goto(`/reports/${report.id}`)
    await expect(page.locator('.banner.mine')).toBeVisible()
    await page.locator('section', { has: page.locator('.secTitle', { hasText: 'Sumário Executivo' }) }).getByLabel('No documento').uncheck()
    await page.getByRole('button', { name: 'Adicionar seção' }).click()
    const extra = page.locator('.extra').last()
    await extra.locator('.extraHead input[maxlength="200"]').fill('Bastidores')
    await extra.getByLabel('No documento').uncheck()
    await page.getByRole('button', { name: 'Salvar', exact: true }).click()
    await expect.poll(async () => (await api(`/reports/${report.id}`, { token: alice.token })).data.export_hidden).toEqual(['executive_summary'])
    const saved = (await api(`/reports/${report.id}`, { token: alice.token })).data
    expect(saved.sections.map((s) => [s.title, s.exported])).toEqual([['Bastidores', false]])

    await page.getByRole('button', { name: 'Parar de editar' }).click()
    await expect(page.locator('section', { has: page.locator('.secTitle', { hasText: 'Bastidores' }) }).locator('.exportToggle')).toHaveText('Fora do documento')
  })
})
