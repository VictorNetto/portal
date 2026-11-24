import { expect, test } from '@playwright/test'
import { adminToken, createUser } from '../support/api.js'
import { loginUI } from '../support/ui.js'

// The guide is a book: numbered chapters in the sidebar, one page at a time, Previous / Next.
const chapterTitles = (page) => page.locator('.toc .chapterLink')
const sectionsOf = (page, chapter) =>
  page.locator('.toc .chapters > li', { has: page.locator(`.chapterLink:has-text("${chapter}")`) }).locator('.sections .tocLink')

const ADMIN_CHAPTERS = [
  'Introdução', '1.Primeiros passos', '2.Vulnerabilidades', '3.Relatórios', '4.Templates',
  '5.Operações: encontrar e exportar', '6.Logs de auditoria', '7.A API de integração', '8.Dashboards',
  '9.Administração', '10.O time de defesa no portal',
]

test.describe('documentation', () => {
  test('reads like a book: chapters, one page at a time, previous and next, the arrow keys', async ({ page }) => {
    await loginUI(page, 'admin', 'admin')
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Documentação")')
    await expect(page).toHaveURL(/\/docs\/introducao$/)
    await expect(page.locator('.page h1')).toHaveText('Introdução')
    await expect(chapterTitles(page)).toHaveText(ADMIN_CHAPTERS)
    await expect(sectionsOf(page, 'Vulnerabilidades')).toHaveText([
      '2.1.Criar uma vulnerabilidade', '2.2.Textos, imagens e anexos', '2.3.O ciclo de vida',
      '2.4.Depois do envio: o RVS e os ajustes', '2.5.Edições simultâneas',
    ])

    await page.click('.pager .next')                                          // a chapter opens with its own page
    await expect(page).toHaveURL(/\/docs\/primeiros-passos$/)
    await expect(page.locator('.page .eyebrow')).toHaveText('Capítulo 1')
    await expect(page.locator('.inChapter a')).toHaveCount(4)

    await page.keyboard.press('ArrowRight')
    await expect(page).toHaveURL(/\/docs\/inicio$/)
    await expect(page.locator('.page h1')).toHaveText('Entrando e se localizando')
    await expect(page.locator('.page .eyebrow')).toHaveText('1. Primeiros passos')
    await expect(page.locator('.toc .tocLink.current')).toHaveText('1.1.Entrando e se localizando')
    await page.keyboard.press('ArrowLeft')
    await expect(page).toHaveURL(/\/docs\/primeiros-passos$/)

    await page.click('.toc .tocLink:has-text("O ciclo de vida")')
    await expect(page).toHaveURL(/\/docs\/vuln-ciclo$/)
    await expect(page.locator('.pager .prev .where')).toHaveText('2.2. Textos, imagens e anexos')
    await expect(page.locator('.pager .next .where')).toHaveText('2.4. Depois do envio: o RVS e os ajustes')
  })

  test('links between pages stay in the tab, old anchors land on their page, tables render, search finds text', async ({ page, context }) => {
    await loginUI(page, 'admin', 'admin')
    await page.goto('/docs/introducao')
    await page.click('.prose a:has-text("Papéis e acesso")')
    await expect(page).toHaveURL(/\/docs\/papeis$/)
    expect(context.pages()).toHaveLength(1)
    await expect(page.locator('.prose table tbody tr')).toHaveCount(8)       // one row per role

    await page.goto('/docs#rvs')                                              // the one-page guide's anchors
    await expect(page).toHaveURL(/\/docs\/vuln-apos$/)
    await page.goto('/docs/nao-existe')
    await expect(page).toHaveURL(/\/docs\/introducao$/)

    await page.fill('.toc .search', 'if_updated_at')
    await expect(page.locator('.results .hit').first()).toContainText('Criar e editar vulnerabilidades')
    await page.locator('.results .hit').first().click()
    await expect(page).toHaveURL(/\/docs\/api-criar$/)
    await expect(page.locator('.toc .search')).toHaveValue('')
  })

  test('the API chapter: the endpoint table, keys, and a curl example on every endpoint page', async ({ page }) => {
    const writer = await createUser(await adminToken(), 'write_all')
    await loginUI(page, writer.username, writer.password)
    await page.goto('/docs/api')
    await expect(page.locator('.page h1')).toHaveText('A API de integração')
    await expect(page.locator('.prose table tbody tr')).toHaveCount(14)
    await expect(sectionsOf(page, 'A API de integração')).toHaveText([
      /Chaves, escopos e autenticação/, /Formatos, paginação e sincronização/, /Lendo vulnerabilidades/,
      /Criar e editar vulnerabilidades/, /Lotes/, /Importar vulnerabilidades antigas/, /A fila de RVS/,
      /Lendo relatórios/, /Erros, monitoração e boas práticas/,
    ])
    await page.goto('/docs/api-chaves')
    await expect(page.locator('.prose pre').first()).toContainText('X-API-Key')
    await page.goto('/docs/api-convencoes')
    await expect(page.locator('.prose pre').last()).toContainText('def changed_since')
    for (const id of ['api-ler', 'api-criar', 'api-lotes', 'api-importar', 'api-rvs', 'api-relatorios']) {
      await page.goto(`/docs/${id}`)
      await expect(page.locator('.prose pre', { hasText: 'curl -sS' }).first()).toBeVisible()
    }
    await expect(chapterTitles(page)).not.toContainText(['Administração', 'Logs de auditoria', 'Dashboards'])
  })

  test('each role sees its chapters; an auditor gets the audit logs; a reader neither API nor templates', async ({ page }) => {
    const auditor = await createUser(await adminToken(), 'auditor')
    await loginUI(page, auditor.username, auditor.password)
    await page.goto('/docs')
    await expect(chapterTitles(page)).toHaveText([
      'Introdução', '1.Primeiros passos', '2.Vulnerabilidades', '3.Relatórios',
      '4.Operações: encontrar e exportar', '5.Logs de auditoria',
    ])
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Sair")')

    const reader = await createUser(await adminToken(), 'read_all')
    await loginUI(page, reader.username, reader.password)
    await page.goto('/docs/api')                                              // not for this role: back to the start
    await expect(page).toHaveURL(/\/docs\/introducao$/)
    await expect(chapterTitles(page)).toHaveText([
      'Introdução', '1.Primeiros passos', '2.Vulnerabilidades', '3.Relatórios', '4.Operações: encontrar e exportar',
    ])
    await page.goto('/docs/sessao')
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("English")')
    await expect(page.locator('.page h1')).toHaveText('The session')
    await expect(chapterTitles(page).nth(1)).toHaveText('1.Getting started')
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Português")')
  })
})
