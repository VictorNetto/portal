// Dashboards (D18): the dashboard role, the editor with live previews, variables and TV links.
import { expect, test } from '@playwright/test'
import { adminToken, api, cleanup, createUser, savedVuln, tag } from '../support/api.js'
import { autoDialogs, collectPageErrors, filterHub, loginUI, rowCount } from '../support/ui.js'

let admin
let painel
const vulns = []
const boards = []
const SHOTS = process.env.E2E_SHOTS // a folder: save screenshots there to look at the pages

test.beforeAll(async () => {
  admin = await adminToken()
  painel = await createUser(admin, 'dashboard')
})
test.afterAll(async () => {
  for (const id of boards) await api(`/dashboards/${id}`, { token: admin, method: 'DELETE' })
  await cleanup(admin, { vulns })
})

async function loginDashboard(page) {
  await page.goto('/login')
  await page.fill('input[autocomplete=username]', painel.username)
  await page.fill('input[type=password]', painel.password)
  await page.click('button')
  await expect(page).toHaveURL(/\/dashboards$/)
}

async function board(charts, variables = []) {
  const { status, data } = await api('/dashboards', {
    token: admin, body: { name: `e2e-${tag()}`, variables, charts: charts.map((query) => ({ query })) },
  })
  expect(status).toBe(201)
  boards.push(data.id)
  return data
}

test('a dashboard account sees only the dashboards', async ({ page }) => {
  await loginDashboard(page)
  await expect(page.locator('.sidebar .navItem')).toHaveCount(1)
  await expect(page.locator('.sidebar .navItem[aria-label="Dashboards"]')).toBeVisible()
  await page.goto('/hub')
  await expect(page).toHaveURL(/\/dashboards$/)
  await page.goto('/users')
  await expect(page).toHaveURL(/\/dashboards$/)
})

test('the editor previews each query and refuses one with an error', async ({ page }) => {
  const errors = collectPageErrors(page)
  autoDialogs(page)
  await loginDashboard(page)
  await page.click('text=Novo dashboard')
  const name = `e2e-${tag()}`
  await page.locator('.formCard input').first().fill(name)
  await page.click('text=Adicionar variável')
  await page.locator('.vname').fill('aberta')
  await page.locator('.vvalue').fill('sent,fixing,retesting')

  const first = page.locator('.chartEdit').first()
  await first.locator('textarea').fill('count where status:$aberta title "Abertas agora"')
  await expect(first.locator('.dval')).toBeVisible()
  await expect(first.locator('.dtitle')).toHaveText('Abertas agora')

  await page.click('text=Adicionar gráfico')
  const second = page.locator('.chartEdit').nth(1)
  await second.locator('textarea').fill('count by severity over fixed per week where fixed:12w')
  await expect(second.locator('.err')).toContainText('período inválido em "fixed:12w"')
  await expect(second.locator('.err')).toContainText('(posição 45)')
  await page.click('button:has-text("Salvar")')
  await expect(page.locator('.pageTop + .err')).toHaveText('Corrija as consultas com erro antes de salvar.')

  await second.locator('textarea').fill('count by report where status:$aberta')
  await expect(second.locator('svg.dsvg')).toBeVisible()
  await expect(second).toContainText('Fica fora dos links de TV')
  await page.click('button:has-text("Salvar")')
  await expect(page).toHaveURL(/\/dashboards\/[0-9a-f-]+$/)
  await expect(page.locator('h1')).toHaveText(name)
  await expect(page.locator('.card')).toHaveCount(2)
  boards.push(page.url().split('/').pop())
  expect(errors).toEqual([])
})

test('variables can change for one view only', async ({ page }) => {
  const v = await savedVuln(admin, { identifier: `e2e-${tag()}`, cvss_score: 9.5 })
  vulns.push(v.id)
  const d = await board(['count where status:$st cvss:9 title "Críticas"'], [{ name: 'st', value: 'fixed' }])
  await loginDashboard(page)
  await page.goto(`/dashboards/${d.id}`)
  const before = Number(await page.locator('.dval').textContent())
  await page.locator('.vars input').fill('ready')
  await page.click('button:has-text("Aplicar")')
  await expect(page.locator('button:has-text("Restaurar")')).toBeVisible()
  await expect.poll(async () => Number(await page.locator('.dval').textContent())).toBeGreaterThanOrEqual(1)
  await page.click('button:has-text("Restaurar")')
  await expect.poll(async () => Number(await page.locator('.dval').textContent())).toBe(before)
  const saved = await api(`/dashboards/${d.id}`, { token: admin })
  expect(saved.data.variables).toEqual([{ name: 'st', value: 'fixed' }])
})

test('a TV link shows the board without signing in, until revoked', async ({ page, browser }) => {
  autoDialogs(page)
  const d = await board([
    'count where status:sent,fixing,retesting title "Abertas"',
    'count by severity where status:sent,fixing,retesting title "Por severidade"',
    'count by severity over fixed per month where fixed:6m as bar title "Corrigidas por mês"',
  ])
  await loginDashboard(page)
  await page.goto(`/dashboards/${d.id}`)
  await expect(page.locator('.card svg, .card .dval').first()).toBeVisible()
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/dash-view.png`, fullPage: true })
  await page.click('text=Novo link de TV')
  await page.fill('.linkForm input', 'Sala do SOC')
  await page.click('text=Criar link')
  const url = await page.locator('.plaintext').textContent()
  expect(url).toMatch(/\/tv\/[\w-]{40,}$/)

  const tv = await (await browser.newContext({ viewport: { width: 1920, height: 1080 } })).newPage()
  await tv.goto(url)
  await expect(tv.locator('.tvHead h1')).toHaveText(d.name)
  await expect(tv.locator('.tile')).toHaveCount(3)
  await expect(tv.locator('.tile .dtitle').nth(2)).toHaveText('Corrigidas por mês')
  if (SHOTS) await tv.screenshot({ path: `${SHOTS}/dash-tv.png` })

  await page.click('button:has-text("Pronto")')
  await page.click('.links .link.danger')
  await expect(page.locator('.links .pill.off')).toHaveText('Revogado')
  await tv.reload()
  await expect(tv.locator('.gone')).toHaveText('Este link não está mais disponível.')
})

test('a TV link is refused while a chart names reports or people', async ({ page }) => {
  const d = await board(['count by operator'])
  await loginDashboard(page)
  await page.goto(`/dashboards/${d.id}`)
  await page.click('text=Novo link de TV')
  await page.fill('.linkForm input', 'Sala')
  await page.click('text=Criar link')
  await expect(page.locator('.links .err')).toContainText('links de TV não mostram "operator"')
})

test('the Hub accepts status:a,b as either', async ({ page }) => {
  const a = await savedVuln(admin, { identifier: `e2e-either-${tag()}` })
  vulns.push(a.id)
  await loginUI(page, 'admin', process.env.E2E_ADMIN_PASSWORD || 'admin')
  await filterHub(page, `e2e-either status:ready,fixing`)
  expect(await rowCount(page)).toBe(1)
  await filterHub(page, `e2e-either status:sent,fixing`)
  expect(await rowCount(page)).toBe(0)
})

test('the example dashboards render', async ({ page }) => {
  const errors = collectPageErrors(page)
  await page.setViewportSize({ width: 1440, height: 1500 })
  await loginUI(page, 'admin', process.env.E2E_ADMIN_PASSWORD || 'admin')
  await page.click('.sidebar .navItem[aria-label="Dashboards"]')
  await expect(page.locator('.clickRow').first()).toBeVisible()
  for (const name of ['Remediação', 'Trimestre']) {
    const row = page.locator('.clickRow', { hasText: name })
    if (!(await row.count())) continue // dev data not loaded
    await row.click()
    await expect(page.locator('.card').first()).toBeVisible()
    await expect(page.locator('.card .derr')).toHaveCount(0)
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/dash-${name === 'Remediação' ? 'remediacao' : 'trimestre'}.png`, fullPage: true })
    await page.goBack()
    await expect(page.locator('.clickRow').first()).toBeVisible()
  }
  expect(errors).toEqual([])
})
