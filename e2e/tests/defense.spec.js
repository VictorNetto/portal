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
