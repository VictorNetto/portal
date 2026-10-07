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
      query: 'Buscar',
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
    users: {
      title: 'Usuários',
      subtitle: 'Gerencie contas e permissões dos operadores.',
      newUser: 'Novo usuário',
      username: 'Usuário',
      password: 'Senha',
      role: 'Função',
      status: 'Situação',
      active: 'Ativo',
      inactive: 'Inativo',
      activate: 'Ativar',
      deactivate: 'Desativar',
      resetPassword: 'Redefinir senha',
      create: 'Criar',
      cancel: 'Cancelar',
      save: 'Salvar',
      mustChange: 'troca obrigatória',
    },
    roles: {
      admin: 'Administrador',
      writer_all: 'Editor',
      reader_all: 'Leitor',
      auditor: 'Auditor',
    },
    rvs: {
      title: 'Fila RVS',
      subtitle: 'Vulnerabilidades disparadas aguardando um ID de RVS.',
      rvsId: 'ID do RVS',
      enter: 'Registrar',
      placeholder: 'ex.: RVS-2026-001',
      empty: 'Nenhuma vulnerabilidade aguardando RVS.',
      dispatchedAt: 'Disparada em',
    },
    actions: { dispatch: 'Disparar' },
    apiKeys: {
      title: 'Chaves de API',
      subtitle: 'Chaves para integrações máquina-a-máquina (scanners, pipelines).',
      newKey: 'Nova chave',
      label: 'Rótulo',
      role: 'Função',
      prefix: 'Prefixo',
      created: 'Criada',
      status: 'Situação',
      active: 'Ativa',
      revoked: 'Revogada',
      revoke: 'Revogar',
      create: 'Criar',
      cancel: 'Cancelar',
      empty: 'Nenhuma chave de API.',
      copyWarn: 'Copie a chave agora — ela não será exibida novamente.',
      copy: 'Copiar',
      copied: 'Copiado!',
      done: 'Pronto',
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
