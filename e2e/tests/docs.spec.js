import { expect, test } from '@playwright/test'
import { adminToken, createUser } from '../support/api.js'
import { loginUI } from '../support/ui.js'

const sectionTitles = (page) => page.locator('.docSection .secHead')
const subTitles = (page, id) => page.locator(`#doc-${id} .docCard h3`)

test.describe('documentation', () => {
  test('opens from the profile menu; sections with subsections; the contents jump to a topic', async ({ page }) => {
    await loginUI(page, 'admin', 'admin')
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Documentação")')
    await expect(page).toHaveURL(/\/docs$/)
    await expect(page.locator('.titleBlock h1')).toHaveText('Documentação')
    const ALL = ['Informações Gerais', 'Vulnerabilidades', 'Relatórios e Templates', 'API', 'Time de defesa', 'Gerenciamento']
    await expect(sectionTitles(page)).toHaveText(ALL)
    await expect(page.locator('.toc .tocSection')).toHaveText(ALL)
    await expect(subTitles(page, 'geral')).toContainText(['Primeiros passos', 'Sessão'])
    await expect(subTitles(page, 'geral')).not.toContainText(['Logs de auditoria'])                  // admins read it under Gerenciamento
    await expect(subTitles(page, 'gerenciamento')).toHaveText(['Usuários', 'Acesso de cada usuário', 'Chaves de API', 'Aprovação de templates', 'Reservas de relatório', 'Logs de auditoria'])
    await expect(subTitles(page, 'vulnerabilidades')).toHaveText(['Criar uma vulnerabilidade', 'Ciclo de vida', 'Depois do envio', 'Edições simultâneas', 'RVS'])

    await page.click('.toc .tocItem:text-is("RVS")')
    await expect(page).toHaveURL(/\/docs#rvs$/)
    await expect(page.locator('#doc-rvs')).toBeInViewport()
    await expect(page.locator('.toc .tocItem.current')).toHaveText('RVS')

    await page.click('.toc .tocSection:has-text("Relatórios e Templates")')                // a section jumps to its first topic
    await expect(page).toHaveURL(/\/docs#relatorios$/)
    await expect(page.locator('#doc-rel-criar')).toBeInViewport()
  })

  test('the API section documents the endpoint, the key roles and examples', async ({ page }) => {
    const writer = await createUser(await adminToken(), 'write_all')
    await loginUI(page, writer.username, writer.password)
    await page.goto('/docs')
    await page.click('.toc .tocSection:text-is("API")')
    await expect(page.locator('#doc-api-visao')).toBeInViewport()
    await expect(subTitles(page, 'api')).toHaveText([
      'Visão geral', 'Chaves e escopos', 'Autenticação', 'Convenções: referências, paginação e sincronização',
      'Listar vulnerabilidades', 'Ler uma vulnerabilidade', 'Evidências de uma vulnerabilidade', 'Baixar uma evidência',
      'Exportar uma vulnerabilidade', 'Fila RVS', 'Registrar o ID de RVS', 'Criar uma vulnerabilidade',
      'Listar relatórios', 'Ler um relatório', 'Exportar um relatório', 'Verificar o portal', 'Erros', 'Boas práticas',
    ])
    await expect(page.locator('#doc-api-auth pre')).toContainText('X-API-Key')
    await expect(page.locator('#doc-api-convencoes pre').last()).toContainText('def changed_since')
    // every endpoint page states its method, path and scope, and shows a curl example
    for (const id of ['vulns', 'vuln', 'vuln-atts', 'att', 'vuln-export', 'rvsq', 'rvs', 'reports', 'report', 'report-export']) {
      await expect(page.locator(`#doc-api-ep-${id} .mdView p`).first()).toContainText(/(GET|POST) \/api\/v1\//)
      await expect(page.locator(`#doc-api-ep-${id} pre`).first()).toContainText('curl -sS')
    }
    await expect(page.locator('#doc-api-ep-rvs')).toContainText('RVS ID is already set')
    await expect(subTitles(page, 'relatorios')).toContainText(['Templates', 'Salvar como Template', 'Compartilhamento e aprovação'])
  })

  test('Gerenciamento is for admins only; an auditor still finds the audit log topic', async ({ page }) => {
    const auditor = await createUser(await adminToken(), 'auditor')
    await loginUI(page, auditor.username, auditor.password)
    await page.goto('/docs')
    await expect(sectionTitles(page)).toHaveText(['Informações Gerais', 'Vulnerabilidades', 'Relatórios e Templates'])
    await expect(page.locator('#doc-gerenciamento')).toHaveCount(0)
    await expect(subTitles(page, 'geral').last()).toHaveText('Logs de auditoria')
  })

  test('a reader sees only the topics for what they can use, in their language', async ({ page }) => {
    const reader = await createUser(await adminToken(), 'read_all')
    await loginUI(page, reader.username, reader.password)
    await page.goto('/docs#sessao')
    await expect(page.locator('#doc-sessao')).toBeInViewport()
    await expect(sectionTitles(page)).toHaveText(['Informações Gerais', 'Vulnerabilidades', 'Relatórios e Templates'])   // no API
    await expect(subTitles(page, 'relatorios')).toHaveText(['Criar um relatório', 'Edição e reserva', 'Conteúdo', 'Envio, progresso e exclusão'])
    await expect(page.locator('.docCard h3:text-is("Logs de auditoria")')).toHaveCount(0)
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("English")')
    await expect(page.locator('.titleBlock h1')).toHaveText('Documentation')
    await expect(sectionTitles(page)).toHaveText(['General Information', 'Vulnerabilities', 'Reports & Templates'])
    await page.click('.profileBtn')
    await page.click('.profileMenu .menuItem:has-text("Português")')
  })
})
