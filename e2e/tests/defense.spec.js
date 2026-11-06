import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, newReport, pngBuffer, recordRvs, reportVuln, savedVuln, tag } from '../support/api.js'

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

// A vuln in fixing, for an RVS id that is already taken.
async function fixingRvs() {
  const v = await savedVuln(admin, { identifier: `e2e-used-${tag()}` })
  vulns.push(v.id)
  await api(`/vulnerabilities/${v.id}/send`, { token: admin, method: 'POST' })
  return (await recordRvs(v.id)).data
}

// Opens a section from the left rail.
const section = (page, label) => page.click(`.sidebar .navItem[aria-label="${label}"]`)

async function loginDefense(page) {
  await page.goto('/login')
  await page.fill('input[autocomplete=username]', defense.username)
  await page.fill('input[type=password]', defense.password)
  await page.click('button')
  await expect(page).toHaveURL(/\/defense\/new$/)
}

test('the defense team accepts a received vuln and records its RVS id', async ({ page }) => {
  const id = `e2e-def-${tag()}`
  await sentWithEvidence(id)
  await loginDefense(page)

  // Its own rail, nothing of the red team's.
  // Its own rail: one item per section, nothing of the red team's.
  await expect(page.locator('.sidebar .navItem .navLabel')).toHaveText(['Novas', 'Aguardando RVS', 'Em andamento', 'Corrigidas', 'Risco assumido'])
  await page.click('.profileBtn')
  await expect(page.locator('.menuItem', { hasText: 'Documentação' })).toHaveCount(1)       // its own guide
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

  // The breadcrumb leads back to Novas, where it was opened; it now lives in "Em andamento".
  await expect(page.locator('.crumbs a')).toHaveText('Novas')
  await expect(page.locator('.sidebar .navItem.active')).toHaveAttribute('aria-label', 'Novas')
  await page.click('.crumbs a')
  await expect(page).toHaveURL(/\/defense\/new$/)
  await section(page, 'Em andamento')
  await expect(page.locator('tbody tr', { hasText: id })).toContainText(rvs)
})

test('red-team pages are out of reach for a defense account', async ({ page }) => {
  await loginDefense(page)
  for (const path of ['/hub', '/users', '/reports/new']) {
    await page.goto(path)
    await expect(page).toHaveURL(/\/defense\/new$/)
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
  await section(page, 'Aguardando RVS')
  await expect(page.locator('.filterbar input')).toHaveValue('')                 // each section starts clean
  await page.fill('.filterbar input', `e2e-batch-${u}`)
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
  await expect(page).toHaveURL(/\/defense\/new$/)                           // it selects, it does not open
  await expect(page.locator('tbody tr.selected')).toHaveCount(2)
  await page.locator('tbody .repLink', { hasText: name }).first().click()
  await expect(page.locator('.selectionHint')).toHaveCount(0)

  // Not a link where nothing can be done with the selection.
  await section(page, 'Em andamento')
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

  await section(page, 'Aguardando RVS')
  await filter()
  await openMenu()
  await expect(menu).toHaveText(['Registrar RVS', 'Assumir risco'])
  await menu.filter({ hasText: 'Assumir risco' }).click()
  await page.locator('.appDialog .modal input').fill('Sistema em desativação')
  await okDialog()
  await expect(page.locator('.ok.msg')).toContainText('2')

  await section(page, 'Risco assumido')
  await filter()
  await openMenu()
  await expect(menu).toHaveText(['Desfazer risco assumido'])
  await menu.click()
  await okDialog()
  await expect(page.locator('.ok.msg')).toContainText('2')

  // Undone, they were accepted before: back to waiting for their RVS, one id each.
  await section(page, 'Aguardando RVS')
  await filter()
  await openMenu()
  await menu.filter({ hasText: 'Registrar RVS' }).click()
  const form = page.locator('.rvsModal')
  const fields = form.locator('.rvsRow input')
  await expect(form.locator('.rvsRow .who')).toHaveText([new RegExp(`e2e-tabs-${u}-[ab]`), new RegExp(`e2e-tabs-${u}-[ab]`)])
  const used = (await fixingRvs()).rvs_id                                        // an id another vuln already has
  const rvsA = `RVS-e2e-${tag()}`
  await fields.nth(0).fill(rvsA)
  await fields.nth(1).fill(` ${rvsA.toLowerCase()}`)
  await form.locator('.btn.primary').click()
  await expect(form.locator('.fieldErr')).toHaveText(['ID repetido nesta lista.', 'ID repetido nesta lista.'])
  await fields.nth(1).fill(used)
  await form.locator('.btn.primary').click()
  await expect(form.locator('.rvsRow')).toHaveCount(1)                            // the first was recorded
  await expect(form.locator('.fieldErr')).toContainText('already used')
  const rvsB = `RVS-e2e-${tag()}`
  await fields.nth(0).fill(rvsB)
  await form.locator('.btn.primary').click()
  await expect(form).toHaveCount(0)

  await section(page, 'Em andamento')
  await filter()
  await expect(page.locator('tbody tr', { hasText: rvsA })).toHaveCount(1)
  await expect(page.locator('tbody tr', { hasText: rvsB })).toHaveCount(1)
  await expect(page.locator('tbody .check, thead .check')).toHaveCount(0)       // nothing to do here
})

test('the documentation shows the defense team only its own guide', async ({ page }) => {
  await loginDefense(page)
  await page.click('.profileBtn')
  await page.click('.profileMenu .menuItem:has-text("Documentação")')
  await expect(page).toHaveURL(/\/docs$/)
  await expect(page.locator('.docSection .secHead')).toHaveText(['Time de defesa'])
  await expect(page.locator('#doc-defesa .docCard h3')).toHaveText([
    'Primeiros passos', 'Sessão', 'As seções', 'Uma vulnerabilidade', 'Aceitar e registrar o RVS',
    'Assumir o risco', 'Várias vulnerabilidades de uma vez', 'Filtros', 'Depois do RVS', 'Registro das ações',
  ])
  await expect(page.locator('#doc-def-secoes li')).toHaveCount(5)
  await expect(page.locator('#doc-def-filtros code').first()).toHaveText('/')
  await page.click('.toc .tocItem:has-text("Assumir o risco")')
  await expect(page.locator('#doc-def-risco')).toBeInViewport()
})
