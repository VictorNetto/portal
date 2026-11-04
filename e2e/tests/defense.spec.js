import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, pngBuffer, savedVuln, tag } from '../support/api.js'

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
  await expect(page.locator('.pageActions .btn')).toHaveCount(0)
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

test('an RVS recorded by the red team fills the Aceita step', async ({ page }) => {
  const v = await savedVuln(admin, { identifier: `e2e-tl-${tag()}` })
  vulns.push(v.id)
  await api(`/vulnerabilities/${v.id}/send`, { token: admin, method: 'POST' })
  await api(`/vulnerabilities/${v.id}/rvs`, { token: admin, body: { rvs_id: `RVS-e2e-${tag()}` } })
  await page.goto('/login')
  await page.fill('input[autocomplete=username]', 'admin')
  await page.fill('input[type=password]', process.env.E2E_ADMIN_PASSWORD || 'admin')
  await page.click('button')
  await expect(page).toHaveURL(/\/hub/)
  await page.goto(`/vulnerabilities/${v.id}`)
  const accepted = page.locator('.timeline .step', { hasText: 'Aceita' })
  await expect(accepted).toHaveClass(/reached/)
  await expect(accepted.locator('.when')).not.toHaveText('—')
})
