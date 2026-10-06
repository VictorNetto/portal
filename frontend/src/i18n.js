// Minimal i18n. PT-BR is the primary language (FRONTEND_SPEC §3). Strings live
// here so an EN toggle can be added later without touching components.
import { ref } from 'vue'

const messages = {
  'pt-BR': {
    brand: 'Portal Red Team',
    nav: {
      hub: 'Central Operacional',
      createVuln: 'Criar Vulnerabilidade',
      createReport: 'Criar Relatório',
      rvsQueue: 'Fila RVS',
      audit: 'Logs de Auditoria',
      users: 'Usuários',
      apiKeys: 'Chaves de API',
      settings: 'Configurações',
    },
    hub: {
      title: 'Central Operacional',
      subtitle: 'Gerencie vulnerabilidades e relatórios de operações de segurança.',
      tabVulns: 'Vulnerabilidades',
      tabReports: 'Relatórios',
      filters: 'Filtros',
      actions: 'Ações',
      createVuln: 'Criar Vulnerabilidade',
      createReport: 'Criar Relatório',
      selected: 'selecionados',
      rows: 'Linhas',
      showing: 'Mostrando',
      of: 'de',
      empty: 'Nenhum registro encontrado.',
    },
    cols: {
      identifier: 'Identificador',
      status: 'Status',
      cvss: 'CVSS',
      operators: 'Operadores',
      source: 'Fonte',
      actions: 'Ações',
      name: 'Nome',
      client: 'Cliente',
    },
    rowActions: {
      view: 'Visualizar',
      detail: 'Detalhar',
      edit: 'Editar',
      send: 'Enviar',
      delete: 'Excluir',
    },
    signOut: 'Sair',
    comingSoon: 'Em breve',
  },
}

export const locale = ref('pt-BR')

export function t(path) {
  const parts = path.split('.')
  let node = messages[locale.value]
  for (const p of parts) {
    node = node?.[p]
    if (node === undefined) return path
  }
  return node
}
