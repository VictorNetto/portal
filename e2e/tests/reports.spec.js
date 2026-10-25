import { readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { adminToken, cleanup, createUser, login, newReport, pdfFile, pngFile, reportVuln, tag } from '../support/api.js'
import { autoDialogs, collectPageErrors, loginUI, navTo } from '../support/ui.js'

let admin
let alice
let bob
const reports = []

test.beforeAll(async () => {
  admin = await adminToken()
  alice = await createUser(admin, 'write_all')
  bob = await createUser(admin, 'write_all')
})
test.afterAll(async () => cleanup(admin, { reports }))

test.describe('reports', () => {
  test('the end date can never come before the start date', async ({ page }) => {
    await loginUI(page, alice.username, alice.password)
    await page.goto('/reports/new')
    const [start, end] = [page.locator('.createCard input[type=date]').nth(0), page.locator('.createCard input[type=date]').nth(1)]
    await start.fill('2026-09-10')
    await expect(end).toHaveAttribute('min', '2026-09-10')                        // the picker offers no earlier day
    await end.fill('2026-09-01')
    await expect(end).toHaveValue('2026-09-10')                                  // a typed earlier end is pulled up
    await end.fill('2026-09-15')
    await start.fill('2026-09-20')
    await expect(end).toHaveValue('2026-09-20')                                  // moving the start past the end too
  })

  test('create a report, fill it in, order its sections and add a vulnerability', async ({ page }) => {
    const errors = collectPageErrors(page)
    autoDialogs(page)
    await loginUI(page, alice.username, alice.password)

    await navTo(page, 'Criar Relatório')
    await expect(page).toHaveURL(/\/reports\/new$/)
    expect(await page.evaluate(() => document.documentElement.dataset.entity)).toBe('reports')   // indigo accent

    const name = `e2e-${tag()}`
    await page.fill('.createCard input[maxlength="200"] >> nth=0', name)
    await page.fill('.createCard input[maxlength="200"] >> nth=1', 'ACME S.A.')
    await page.click('.createActions .btn.primary')
    await expect(page).toHaveURL(/\/reports\/[0-9a-f-]{36}$/)
    const id = page.url().split('/').pop()
    reports.push(id)

    // the creator is editing straight away, with the default executive summary in place
    await expect(page.locator('.banner.mine')).toBeVisible()
    await expect(page.locator('.subline .mono')).toHaveText(/OP-\d+/)
    await expect(page.locator('.mdEditor').first().locator('textarea')).toHaveValue(/Objetivo/)

    await page.fill('textarea[maxlength="5000"]', 'Aplicações web e API')
    await page.fill('input[placeholder="infra, web, mobile, API"]', 'web')
    await page.click('button:has-text("Adicionar seção")')
    await page.click('button:has-text("Adicionar seção")')
    await page.locator('.extraHead input').nth(0).fill('Metodologia')
    await page.locator('.extraHead input').nth(1).fill('Limitações')
    await page.locator('.extra').nth(0).locator('textarea').fill('OWASP')
    await page.locator('.extra').nth(0).locator('button:has-text("Descer")').click()
    await page.click('.pageActions button:text-is("Salvar")')
    await expect(page.locator('.ok.msg')).toContainText('salvo')

    await page.reload()                          // leaving releases the lock: take it again
    await page.click('.pageActions button:has-text("Editar")')
    await expect(page.locator('.banner.mine')).toBeVisible()
    await expect(page.locator('.extraHead input')).toHaveCount(2)
    expect(await page.locator('.extraHead input').evaluateAll((els) => els.map((e) => e.value))).toEqual(['Limitações', 'Metodologia'])
    await expect(page.locator('textarea[maxlength="5000"]')).toHaveValue(/API/)

    // a vulnerability inside the report
    await page.click('button:has-text("Adicionar vulnerabilidade")')
    await expect(page).toHaveURL(/\/vulnerabilities\/new$/)
    await expect(page.locator('.pageActions button:has-text("Enviar")')).toHaveCount(0)    // no life of its own
    await page.locator('.infoGrid input').first().fill('RV-1')
    await page.locator('input.cvss').click()
    await page.locator('input.cvss').fill('91')
    await page.keyboard.press('Enter')
    await page.locator('.mdEditor').first().locator('textarea').fill('Falha crítica')
    await page.click('.pageActions button:text-is("Salvar")')
    await expect(page).toHaveURL(/\/vulnerabilities\/[0-9a-f-]{36}$/)
    await expect(page.locator('.banner.mine')).toBeVisible()
    await page.locator('.crumbs a').nth(2).click()                       // back via the report crumb
    await expect(page.locator('.vt .cvss')).toHaveText('9.1')
    await expect(page.locator('.banner.mine')).toBeVisible()             // the lock survived the round trip
    expect(errors).toEqual([])
  })

  test('only one operator edits at a time; an admin can take the lock away', async ({ browser }) => {
    // a report created by alice: she holds its lock from the start
    const own = await newReport(await login(alice.username, alice.password), { name: `e2e-lock-${tag()}` })
    reports.push(own.id)

    const pa = await (await browser.newContext()).newPage()
    const pb = await (await browser.newContext()).newPage()
    const pAdmin = await (await browser.newContext()).newPage()
    for (const p of [pa, pb, pAdmin]) autoDialogs(p)
    await loginUI(pa, alice.username, alice.password)
    await loginUI(pb, bob.username, bob.password)
    await loginUI(pAdmin, 'admin', 'admin')

    // bob sees it read-only and cannot edit
    await pb.goto(`/reports/${own.id}`)
    await expect(pb.locator('.banner.other')).toContainText(alice.username)
    await expect(pb.locator('.grid4 input, .grid4 textarea, .mdEditor, .extraHead')).toHaveCount(0)   // read as a report
    await expect(pb.locator('.pageActions button:has-text("Editar")')).toHaveCount(0)
    await expect(pb.locator('button:has-text("Liberar bloqueio")')).toHaveCount(0)        // not for a writer
    await expect(pb.locator('button:has-text("Parar de editar")')).toHaveCount(0)

    // the admin sees the same plus the force-release control; using it frees the report
    await pAdmin.goto(`/reports/${own.id}`)
    await expect(pAdmin.locator('.banner.other')).toContainText(alice.username)
    await pAdmin.click('button:has-text("Liberar bloqueio")')
    await expect(pAdmin.locator('.pageActions .btn.primary:has-text("Editar")')).toBeVisible()

    // now bob can take it
    await pb.reload()
    await expect(pb.locator('.pageActions .btn.primary:has-text("Editar")')).toBeVisible()
    await pb.click('.pageActions button:has-text("Editar")')
    await expect(pb.locator('.banner.mine')).toBeVisible()

    // alice's page notices on her next action: she no longer holds the lock
    await pa.goto(`/reports/${own.id}`)
    await expect(pa.locator('.banner.other')).toContainText(bob.username)
  })

  test('dispatching a report locks it, releases its vulnerabilities and offers the exports', async ({ page }) => {
    autoDialogs(page, { promptValue: 'Diagrama' })
    const r = await newReport(admin, { name: `e2e-disp-${tag()}`, client_name: 'Globex' })
    reports.push(r.id)
    const rv = await reportVuln(admin, r.id, { identifier: `e2e-rv-${tag()}`, cvss_score: 8.8 })
    await loginUI(page, 'admin', 'admin')
    await page.goto(`/reports/${r.id}`)
    await expect(page.locator('.banner.mine')).toBeVisible()

    // evidence: a file in the bundle, an image embedded in the summary
    await page.locator('.drop input[type=file]').setInputFiles(pdfFile())
    await expect(page.locator('.item .name')).toHaveText('evidence.pdf')
    const summary = page.locator('.mdEditor').first()
    await summary.locator('input[type=file]').setInputFiles(pngFile())
    await expect(summary.locator('textarea')).toHaveValue(/!\[Diagrama\]\(\/api\/attachments\//)
    await expect(page.locator('.item')).toHaveCount(2)

    // exports: one "Exportar" button opens the formats
    const exportAs = async (label) => {
      await page.click('.pageActions .exportWrap > .btn')
      await expect(page.locator('.exportMenu button')).toHaveText(['PDF', 'Excel', 'Word'])
      const [file] = await Promise.all([page.waitForEvent('download'), page.click(`.exportMenu button:text-is("${label}")`)])
      await expect(page.locator('.exportMenu')).toHaveCount(0)                     // the menu closes itself
      return readFileSync(await file.path())
    }
    expect((await exportAs('PDF')).subarray(0, 5).toString()).toBe('%PDF-')
    expect((await exportAs('Excel')).subarray(0, 2).toString()).toBe('PK')
    expect((await exportAs('Word')).subarray(0, 2).toString()).toBe('PK')

    // dispatch
    await page.click('.pageActions button:has-text("Disparar")')
    await expect(page.locator('.subline .pill')).toHaveText('Disparada')
    await expect(page.locator('.grid4 input, .grid4 textarea, .extraHead')).toHaveCount(0)
    await expect(page.locator('.mdEditor')).toHaveCount(1)                       // only the internal notes stay editable
    await expect(page.locator('.drop')).toHaveCount(0)
    await expect(page.locator('.vt .pill')).toHaveText('Disparada')

    // the released vulnerability is now an ordinary record with its own timeline
    await page.click('.vt tbody tr:first-child')
    await expect(page).toHaveURL(/\/vulnerabilities\/[0-9a-f-]{36}$/)
    await expect(page.locator('.timeline')).toBeVisible()
    await expect(page.locator('.titleBlock h1')).toHaveText(/VULN-\d+/)
    void rv
  })

  test('an unfinished report warns before the user leaves', async ({ page }) => {
    const dialogs = autoDialogs(page, { accept: false })
    const r = await newReport(admin, { name: `e2e-warn-${tag()}` })
    reports.push(r.id)
    await loginUI(page, 'admin', 'admin')
    await page.goto(`/reports/${r.id}`)
    await expect(page.locator('.banner.mine')).toBeVisible()
    await page.fill('textarea[maxlength="5000"]', 'escopo editado')
    await page.click('.pageActions button:has-text("Voltar")')
    await expect.poll(() => dialogs.length).toBe(1)
    await expect(page).toHaveURL(/\/reports\//)                          // stayed
  })
})
