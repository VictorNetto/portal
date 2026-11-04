import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, newReport, pngBuffer, reportVuln, savedVuln, tag } from '../support/api.js'

let admin
let defense
const vulns = []

test.beforeAll(async () => {
  admin = await adminToken()
  defense = await createUser(admin, 'defense')
})
test.afterAll(async () => cleanup(admin, { vulns }))

// A sent vuln whose finding embeds an evidence image, as the red team writes them.
async function sentWithEvidence(identifier) {
  const v = await savedVuln(admin, { identifier, internal_notes: `segredo-${identifier}` })
  vulns.push(v.id)
  const form = new FormData()
  form.append('file', new Blob([pngBuffer(40, 20)], { type: 'image/png' }), 'prova.png')
  const res = await fetch(`${process.env.E2E_BASE_URL || 'http://nginx:80'}/api/vulnerabilities/${v.id}/attachments`, {
    method: 'POST', headers: { Authorization: `Bearer ${admin}` }, body: form,
  })
  const att = await res.json()
  await api(`/vulnerabilities/${v.id}`, {
    token: admin, method: 'PATCH',
    body: { version: v.version, finding_detail: `Prova:\n\n![prova](/api/attachments/${att.id}/content)` },
  })
  await api(`/vulnerabilities/${v.id}/send`, { token: admin, method: 'POST' })
  return v
}

async function loginDefense(page) {
  await page.goto('/login')
  await page.fill('input[autocomplete=username]', defense.username)
  await page.fill('input[type=password]', defense.password)
  await page.click('button')
  await expect(page).toHaveURL(/\/defense$/)
}

test('the defense team accepts a received vuln and records its RVS id', async ({ page }) => {
  const id = `e2e-def-${tag()}`
  await sentWithEvidence(id)
  await loginDefense(page)

  // Its own rail, nothing of the red team's.
  await expect(page.locator('.sidebar .navItem:not(.hamb)')).toHaveCount(1)
  await page.click('.profileBtn')
  await expect(page.locator('.menuItem', { hasText: 'Documentação' })).toHaveCount(0)
  await page.click('.profileBtn')

  const row = page.locator('tbody tr', { hasText: id })
  await expect(row).toContainText('Nova')
  await row.click()
  await expect(page).toHaveURL(/\/defense\/vulnerabilities\//)
  await expect(page.locator('h1')).toHaveText(id)
  await expect(page.locator('body')).not.toContainText(`segredo-${id}`)
  const img = page.locator('.mdView img')
  await expect(img).toHaveJSProperty('complete', true)
  expect(await img.evaluate((el) => el.naturalWidth)).toBeGreaterThan(0)

  // No RVS before accepting.
  await expect(page.locator('.rvsForm')).toHaveCount(0)
  await page.click('.pageActions .btn.primary:has-text("Aceitar")')
  await expect(page.locator('.ok.msg')).toContainText('aceita')
  await expect(page.locator('.titleBlock p')).toContainText(`aceita por ${defense.username}`)

  const rvs = `RVS-e2e-${tag()}`
  await page.fill('.rvsForm input', rvs)
  await page.click('.rvsForm .btn.primary')
  await expect(page.locator('.ok.msg')).toContainText('RVS registrado')
  await expect(page.locator('.titleBlock p')).toContainText('Em correção')
  await expect(page.locator('.rvsForm')).toHaveCount(0)
  await expect(page.locator('.timeline .rvs')).toHaveText(rvs)

  // Back on the list it moved to "Em andamento".
  await page.click('.crumbs a')
  await page.click('.tab:has-text("Em andamento")')
  await expect(page.locator('tbody tr', { hasText: id })).toContainText(rvs)
})

test('red-team pages are out of reach for a defense account', async ({ page }) => {
  await loginDefense(page)
  for (const path of ['/hub', '/rvs-queue', '/users', '/reports/new', '/docs']) {
    await page.goto(path)
    await expect(page).toHaveURL(/\/defense$/)
  }
})

test('the defense team assumes the risk instead of fixing, and the red team sees why', async ({ page }) => {
  const id = `e2e-risk-${tag()}`
  const v = await sentWithEvidence(id)
  await loginDefense(page)
  await page.goto(`/defense/vulnerabilities/${v.id}`)
  await page.click('.pageActions .btn:has-text("Assumir risco")')
  const box = page.locator('.appDialog .modal')
  await box.locator('input').fill('Sistema será desativado em dezembro')
  await box.locator('.modalActions .btn', { hasText: 'Assumir risco' }).click()
  await expect(page.locator('.ok.msg')).toContainText('Risco assumido')
  await expect(page.locator('.pageActions .btn')).toHaveText(['Desfazer risco assumido'])  // the only way back
  await expect(page.locator('.timeline .label')).toHaveText(['Recebida', 'Risco assumido'])
  await expect(page.locator('.riskReason')).toContainText('desativado em dezembro')

  const { data } = await api(`/vulnerabilities/${v.id}`, { token: admin })
  expect(data.status).toBe('risk_accepted')
  expect(data.risk_reason).toBe('Sistema será desativado em dezembro')
})

test('batch accept over a filtered selection', async ({ page }) => {
  const u = tag()
  const ids = [`e2e-batch-${u}-a`, `e2e-batch-${u}-b`]
  const made = []
  for (const identifier of ids) {
    const v = await savedVuln(admin, { identifier })
    vulns.push(v.id); made.push(v)
    await api(`/vulnerabilities/${v.id}/send`, { token: admin, method: 'POST' })
  }
  await loginDefense(page)
  await page.fill('.filterbar input', `e2e-batch-${u}`)
  await expect(page.locator('tbody tr:not(:has(td.empty))')).toHaveCount(2)
  await page.click('thead .check')
  await expect(page.locator('.selectionHint')).toContainText('2')
  await page.click('.batchWrap .btn')
  await page.click('.rowMenuInline button:has-text("Aceitar")')
  await page.locator('.appDialog .modal .modalActions .btn').last().click()
  await expect(page.locator('.ok.msg')).toContainText('2')
  // They left "Novas" and wait for their RVS.
  await expect(page.locator('tbody tr:not(:has(td.empty))')).toHaveCount(0)
  await page.click('.tab:has-text("Aguardando RVS")')
  await expect(page.locator('tbody tr:not(:has(td.empty))')).toHaveCount(2)
  for (const v of made) {
    const { data } = await api(`/vulnerabilities/${v.id}`, { token: admin })
    expect(data.accepted_at).toBeTruthy()
  }
})

test('a report name selects its vulns, and a quoted filter keeps spaces', async ({ page }) => {
  const u = tag()
  const name = `e2e Rede ${u} Data Center`
  const r = await newReport(admin, { name })
  const a = await reportVuln(admin, r.id, { identifier: `e2e-pick-${u}-a`, finding_detail: 'f', mitigation: 'm' })
  const b = await reportVuln(admin, r.id, { identifier: `e2e-pick-${u}-b`, finding_detail: 'f', mitigation: 'm' })
  await api(`/reports/${r.id}/lock`, { token: admin, method: 'POST' })
  expect((await api(`/reports/${r.id}/send`, { token: admin, method: 'POST' })).status).toBe(200)
  vulns.push(a.id, b.id)
  const other = await savedVuln(admin, { identifier: `e2e-pick-${u}-other` })
  vulns.push(other.id)
  await api(`/vulnerabilities/${other.id}/send`, { token: admin, method: 'POST' })

  await loginDefense(page)
  const rowsShown = page.locator('tbody tr:not(:has(td.empty))')
  await page.fill('.filterbar input', `report:"Rede ${u} Data"`)
  await page.keyboard.press('Escape')
  await expect(rowsShown).toHaveCount(2)
  // Unquoted, the value stops at the space: "Data" becomes a search on the identifier.
  await page.fill('.filterbar input', `report:${u} Data`)
  await page.keyboard.press('Escape')
  await expect(rowsShown).toHaveCount(0)

  // Clicking the report name selects its vulns (and only them), a second click clears them.
  await page.fill('.filterbar input', `e2e-pick-${u}`)
  await page.keyboard.press('Escape')
  await expect(rowsShown).toHaveCount(3)
  await page.locator('tbody .repLink', { hasText: name }).first().click()
  await expect(page.locator('.selectionHint')).toContainText('2')
  await expect(page).toHaveURL(/\/defense$/)                               // it selects, it does not open
  await expect(page.locator('tbody tr.selected')).toHaveCount(2)
  await page.locator('tbody .repLink', { hasText: name }).first().click()
  await expect(page.locator('.selectionHint')).toHaveCount(0)

  // Not a link where nothing can be done with the selection.
  await page.click('.tab:has-text("Em andamento")')
  await expect(page.locator('tbody .repLink')).toHaveCount(0)
})

test('each tab offers only the batch actions its vulns allow', async ({ page }) => {
  const u = tag()
  const made = []
  for (const s of ['a', 'b']) {
    const v = await savedVuln(admin, { identifier: `e2e-tabs-${u}-${s}` })
    vulns.push(v.id); made.push(v)
    await api(`/vulnerabilities/${v.id}/send`, { token: admin, method: 'POST' })
  }
  await loginDefense(page)
  const menu = page.locator('.rowMenuInline button')
  const openMenu = async () => { await page.click('thead .check'); await page.click('.batchWrap .btn') }
  const filter = async () => { await page.fill('.filterbar input', `e2e-tabs-${u}`); await page.keyboard.press('Escape') }
  const okDialog = () => page.locator('.appDialog .modal .modalActions .btn').last().click()

  await filter()
  await openMenu()
  await expect(menu).toHaveText(['Aceitar', 'Assumir risco'])
  await menu.filter({ hasText: 'Aceitar' }).click()
  await okDialog()

  await page.click('.tab:has-text("Aguardando RVS")')
  await filter()
  await openMenu()
  await expect(menu).toHaveText(['Registrar RVS', 'Assumir risco'])
  await menu.filter({ hasText: 'Assumir risco' }).click()
  await page.locator('.appDialog .modal input').fill('Sistema em desativação')
  await okDialog()
  await expect(page.locator('.ok.msg')).toContainText('2')

  await page.click('.tab:has-text("Risco assumido")')
  await filter()
  await openMenu()
  await expect(menu).toHaveText(['Desfazer risco assumido'])
  await menu.click()
  await okDialog()
  await expect(page.locator('.ok.msg')).toContainText('2')

  // Undone, they were accepted before: back to waiting for the RVS, and one id covers both.
  await page.click('.tab:has-text("Aguardando RVS")')
  await filter()
  await openMenu()
  await menu.filter({ hasText: 'Registrar RVS' }).click()
  const rvs = `RVS-e2e-${tag()}`
  await page.locator('.appDialog .modal input').fill(rvs)
  await okDialog()
  await page.click('.tab:has-text("Em andamento")')
  await filter()
  await expect(page.locator('tbody tr', { hasText: rvs })).toHaveCount(2)
  await expect(page.locator('tbody .check, thead .check')).toHaveCount(0)       // nothing to do here
  for (const v of made) expect((await api(`/vulnerabilities/${v.id}`, { token: admin })).data.rvs_id).toBe(rvs)

  await page.click('.tab:has-text("Todas")')
  await filter()
  await openMenu()
  await expect(menu).toHaveText(['Aceitar', 'Registrar RVS', 'Assumir risco', 'Desfazer risco assumido'])
})
