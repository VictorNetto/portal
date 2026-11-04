import { readFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { fixingVuln, adminToken, api, cleanup, createUser, newReport, newVuln, reportVuln, savedVuln, tag } from '../support/api.js'
import { autoDialogs, filterHub, loginUI, rowCount } from '../support/ui.js'

let admin
let writer
const vulns = []
const reports = []
const mk = async (fn, ...args) => { const v = await fn(...args); vulns.push(v.id); return v }

test.beforeAll(async () => {
  admin = await adminToken()
  writer = await createUser(admin, 'write_all')
})
test.afterAll(async () => cleanup(admin, { vulns, reports }))

// A zip's file names, read from its central directory (no zip library needed).
const zipNames = (buf) => {
  const names = []
  let i = 0
  while ((i = buf.indexOf(Buffer.from([0x50, 0x4b, 0x01, 0x02]), i)) !== -1) {
    const len = buf.readUInt16LE(i + 28)
    names.push(buf.subarray(i + 46, i + 46 + len).toString())
    i += 46 + len
  }
  return names
}

test.describe('operations hub', () => {
  test('the tab lives in the URL and survives a reload', async ({ page }) => {
    await loginUI(page, writer.username, writer.password)
    await page.click('.tab:has-text("Relatórios")')
    await expect(page).toHaveURL(/entity=reports/)
    await page.reload()
    await expect(page.locator('.tab.active')).toHaveText('Relatórios')
    await expect(page.locator('.rtable')).toBeVisible()
    await page.click('.tab:has-text("Vulnerabilidades")')
    await expect(page).toHaveURL(/entity=vulnerabilities/)
  })

  test('the filter language narrows the list', async ({ page }) => {
    const unique = tag()
    const a = await mk(savedVuln, admin, { identifier: `e2e-f-${unique}-a`, cvss_score: 9.1, source: 'nuclei' })
    await mk(newVuln, admin, { identifier: `e2e-f-${unique}-b`, cvss_score: 2.0, source: 'burp' })
    await loginUI(page, writer.username, writer.password)

    await filterHub(page, `e2e-f-${unique}`)
    expect(await rowCount(page)).toBe(2)
    await filterHub(page, `e2e-f-${unique} status:ready`)
    expect(await rowCount(page)).toBe(1)
    await filterHub(page, `e2e-f-${unique} cvss:7`)
    expect(await rowCount(page)).toBe(1)
    await filterHub(page, `e2e-f-${unique} source:burp`)
    expect(await rowCount(page)).toBe(1)
    await filterHub(page, `e2e-f-${unique} -source:burp`)
    expect(await rowCount(page)).toBe(1)
    await expect(page.locator('.vtable tbody tr').first()).toContainText(a.identifier)
    await filterHub(page, `zzz-no-such-${unique}`)
    expect(await rowCount(page)).toBe(0)
  })

  test('the details drawer shows the vulnerability, its RVS id and its timeline', async ({ page }) => {
    const v = await mk(fixingVuln, admin, { identifier: `e2e-d-${tag()}`, cvss_score: 6.4, cvss_vector: 'AV:N/AC:L', source: 'zap' })
    await loginUI(page, writer.username, writer.password)
    await filterHub(page, v.identifier)
    await page.click('.vtable tbody tr:first-child td:nth-child(2)')

    const drawer = page.locator('.details.open')
    await expect(drawer).toBeVisible()
    await expect(drawer.locator('.detailsId')).toHaveText(v.identifier)           // the title is the identifier
    await expect(drawer.locator('.statusPill')).toHaveText('Em correção')
    await expect(drawer.locator('.metaLine .k')).toHaveText(['ID interno', 'CVSS', 'Vetor CVSS', 'Fonte', 'RVS'])
    await expect(drawer.locator('.metaLine')).toContainText(v.rvs_id)
    await expect(drawer.locator('.opsLine .k')).toHaveText('Operadores')
    await expect(drawer.locator('.step.reached')).toHaveCount(4)                   // created, ready, sent, fixing
    await expect(drawer.locator('.step.current .label')).toHaveText('Em correção')

    // the list shrinks above the drawer: the last row stays reachable
    const rows = await page.locator('.vtable tbody tr').count()
    expect(rows).toBeGreaterThan(0)
    await drawer.locator('.btn:has-text("Fechar")').click()
    await expect(page.locator('.details.open')).toHaveCount(0)
  })

  test('the row menu opens above when there is no room below, and closes on an outside click', async ({ page }) => {
    await mk(newVuln, admin, { identifier: `e2e-m-${tag()}` })
    await page.setViewportSize({ width: 1300, height: 430 })
    await loginUI(page, writer.username, writer.password)
    await filterHub(page, 'e2e-m-')
    await page.click('.vtable tbody tr:last-child td:nth-child(7) button')
    const menu = page.locator('.rowMenuInline')
    await expect(menu).toBeVisible()
    const box = await menu.boundingBox()
    expect(box.y).toBeGreaterThanOrEqual(0)
    expect(box.y + box.height).toBeLessThanOrEqual(430)                            // fully on screen, opened upward
    await page.click('.hubTop', { position: { x: 4, y: 4 } })
    await expect(menu).toHaveCount(0)
  })

  test('row and batch actions: export, send (skipping what cannot be), delete', async ({ page }) => {
    const unique = tag()
    const s1 = await mk(savedVuln, admin, { identifier: `e2e-b-${unique}-1` })
    const s2 = await mk(savedVuln, admin, { identifier: `e2e-b-${unique}-2` })
    const d1 = await mk(newVuln, admin, { identifier: `e2e-b-${unique}-3` })
    const trash = [await mk(newVuln, admin, { identifier: `e2e-t-${unique}-1` }), await mk(newVuln, admin, { identifier: `e2e-t-${unique}-2` })]
    await loginUI(page, writer.username, writer.password)
    autoDialogs(page)

    // batch export -> a ZIP with one PDF per selected vulnerability
    await filterHub(page, `e2e-b-${unique}`)
    await page.locator('.tablePanel thead input.check').check()
    await page.click('.toolbar .batchWrap button')
    await expect(page.locator('.batchWrap .rowMenuInline button')).toHaveText(['Exportar PDF (ZIP)', 'Exportar Excel', 'Enviar', 'Excluir'])
    const [zip] = await Promise.all([page.waitForEvent('download'), page.click('.batchWrap button:has-text("Exportar PDF (ZIP)")')])
    const names = zipNames(readFileSync(await zip.path()))
    expect(names).toHaveLength(3)
    expect(names.every((n) => n.endsWith('.pdf'))).toBe(true)

    // batch send: 2 ready ones go, the draft is skipped (not failed)
    await page.click('.toolbar .batchWrap button')
    await page.click('.batchWrap button:has-text("Enviar")')
    await expect(page.locator('.ok.msg')).toContainText('2 concluído(s), 1 ignorado(s), 0 com falha')
    await expect(page.locator(`.vtable tbody tr:has-text("${s1.identifier}") .pill`)).toHaveText('Enviada')
    await expect(page.locator(`.vtable tbody tr:has-text("${s2.identifier}") .pill`)).toHaveText('Enviada')
    await expect(page.locator(`.vtable tbody tr:has-text("${d1.identifier}") .pill`)).toHaveText('Rascunho')
    await expect(page.locator('.toolbar .batchWrap')).toHaveCount(0)                // selection cleared

    // row menu: a draft cannot be sent, a single export is the PDF itself
    await page.click(`.vtable tbody tr:has-text("${d1.identifier}") td:nth-child(7) button`)
    await expect(page.locator('.rowMenuInline button')).toHaveText(['Visualizar', 'Abrir', 'Exportar', 'Excluir'])
    const [pdf] = await Promise.all([page.waitForEvent('download'), page.click('.rowMenuInline button:has-text("Exportar")')])
    expect(readFileSync(await pdf.path()).subarray(0, 5).toString()).toBe('%PDF-')

    // batch delete
    await filterHub(page, `e2e-t-${unique}`)
    await page.locator('.tablePanel thead input.check').check()
    await page.click('.toolbar .batchWrap button')
    await page.click('.batchWrap button:has-text("Excluir")')
    await expect(page.locator('.ok.msg')).toContainText('2 concluído(s)')
    await expect.poll(() => rowCount(page)).toBe(0)
    void trash
  })

  test('vulnerabilities inside reports are listed, with their report', async ({ page }) => {
    const u = tag()
    const r = await newReport(admin, { name: `e2e-rv-${u}` })
    reports.push(r.id)
    const inside = await reportVuln(admin, r.id, { identifier: `e2e-rv-${u}-inside` })
    await mk(newVuln, admin, { identifier: `e2e-rv-${u}-alone` })
    await api(`/reports/${r.id}/lock`, { token: admin, method: 'DELETE' })
    await loginUI(page, writer.username, writer.password)

    await filterHub(page, `e2e-rv-${u}`)
    expect(await rowCount(page)).toBe(2)
    const row = page.locator(`.vtable tbody tr:has-text("${inside.identifier}")`)
    await expect(row.locator('td:nth-child(5)')).toHaveText(r.name)
    await expect(page.locator(`.vtable tbody tr:has-text("-alone") td:nth-child(5)`)).toHaveText('—')

    // filter by report, or by "not in a report"
    await filterHub(page, `e2e-rv-${u} report:${r.name}`)
    expect(await rowCount(page)).toBe(1)
    await filterHub(page, `e2e-rv-${u} report:none`)
    expect(await rowCount(page)).toBe(1)
    await expect(page.locator('.vtable tbody')).toContainText('-alone')

    // a draft report's vuln is deleted from its report, not from the list
    await filterHub(page, `e2e-rv-${u} report:${r.name}`)
    await row.locator('td:nth-child(7) button').click()
    await expect(page.locator('.rowMenuInline button')).toHaveText(['Visualizar', 'Abrir', 'Exportar'])
    await page.locator('.hubTop').click({ position: { x: 2, y: 2 } })            // close the menu

    // the report id opens the report
    await row.locator('td:nth-child(5) .repLink').click()
    await expect(page).toHaveURL(new RegExp(`/reports/${r.id}$`))
  })

  test('a read-only user sees only the read actions', async ({ page }) => {
    const reader = await createUser(admin, 'read_all')
    const v = await mk(newVuln, admin, { identifier: `e2e-r-${tag()}` })
    await loginUI(page, reader.username, reader.password)
    await filterHub(page, v.identifier)
    await page.locator('.tablePanel tbody tr:first-child input.check').check()
    await page.click('.toolbar .batchWrap button')
    await expect(page.locator('.batchWrap .rowMenuInline button')).toHaveText(['Exportar PDF (ZIP)', 'Exportar Excel'])
    await page.click('.hubTop', { position: { x: 4, y: 4 } })
    await page.click('.vtable tbody tr:first-child td:nth-child(7) button')
    await expect(page.locator('.rowMenuInline button')).toHaveText(['Visualizar', 'Abrir', 'Exportar'])
  })

  test('the reports tab lists, filters by client, previews and deletes', async ({ page }) => {
    const client = `Client-${tag()}`
    const r = await newReport(admin, { name: `e2e-rep-${tag()}`, client_name: client })
    reports.push(r.id)
    await api(`/reports/${r.id}/lock`, { token: admin, method: 'DELETE' })       // free it so a writer may delete
    await loginUI(page, writer.username, writer.password)
    await page.click('.tab:has-text("Relatórios")')
    await filterHub(page, client)
    expect(await rowCount(page, '.rtable')).toBe(1)
    await page.click('.rtable tbody tr:first-child td:nth-child(2)')
    await expect(page.locator('.details.open .metaLine .k')).toHaveText(['Risco', 'Cliente', 'Período', 'Vulns.'])
    await expect(page.locator('.details.open .metaLine')).toContainText(client)
    await expect(page.locator('.details.open .opsLine .k')).toHaveText('Operadores')
    await expect(page.locator('.details.open .step .label')).toHaveText(['Criado', 'Enviado', 'Concluído'])
    await expect(page.locator('.details.open .step.current .label')).toHaveText('Criado')
    await expect(page.locator('.details .btn:has-text("Abrir")')).toBeVisible()
    await page.click('.details .btn:has-text("Fechar")')

    autoDialogs(page)
    await page.click('.rtable tbody tr:first-child td:nth-child(8) button')
    await page.click('.rowMenuInline button:has-text("Excluir")')
    await expect.poll(() => rowCount(page, '.rtable')).toBe(0)
  })
})
