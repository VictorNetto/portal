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
      createdAt: 'Criada em',
      updatedAt: 'Atualizada em',
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
    audit: {
      title: 'Logs de Auditoria',
      subtitle: 'Registro de todas as ações no portal.',
      when: 'Quando',
      actor: 'Ator',
      action: 'Ação',
      entity: 'Entidade',
      ip: 'IP',
      detail: 'Detalhe',
      allActions: 'Todas as ações',
      empty: 'Nenhum registro.',
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
    common: {
      prev: 'Anterior',
      next: 'Próxima',
      close: 'Fechar',
      clear: 'Limpar',
      help: 'Ajuda',
      rowMenu: 'Ações',
    },
    profile: {
      menu: 'Perfil',
      language: 'Idioma',
      title: 'Meu perfil',
      placeholder: 'Página de perfil em construção.',
      username: 'Usuário',
      role: 'Função',
    },
    signOut: 'Sair',
    comingSoon: 'Em breve',
  },

  // English. Any key missing here falls back to pt-BR (see t()).
  en: {
    brand: 'Red Team Portal',
    nav: {
      hub: 'Operations Hub',
      createVuln: 'Create Vulnerability',
      createReport: 'Create Report',
      rvsQueue: 'RVS Queue',
      audit: 'Audit Logs',
      users: 'Users',
      apiKeys: 'API Keys',
      settings: 'Settings',
    },
    hub: {
      title: 'Operations Hub',
      subtitle: 'Manage vulnerabilities and reports of security operations.',
      tabVulns: 'Vulnerabilities',
      tabReports: 'Reports',
      actions: 'Actions',
      createVuln: 'Create Vulnerability',
      createReport: 'Create Report',
      selected: 'selected',
      showing: 'Showing',
      of: 'of',
      empty: 'No records found.',
    },
    cols: {
      identifier: 'Identifier',
      status: 'Status',
      cvss: 'CVSS',
      operators: 'Operators',
      source: 'Source',
      createdAt: 'Created',
      updatedAt: 'Updated',
      actions: 'Actions',
      name: 'Name',
      client: 'Client',
    },
    rowActions: { view: 'View', detail: 'Details', edit: 'Edit', send: 'Send', delete: 'Delete' },
    users: {
      title: 'Users',
      subtitle: 'Manage operator accounts and permissions.',
      newUser: 'New user',
      username: 'Username',
      password: 'Password',
      role: 'Role',
      status: 'Status',
      active: 'Active',
      inactive: 'Inactive',
      activate: 'Activate',
      deactivate: 'Deactivate',
      resetPassword: 'Reset password',
      create: 'Create',
      cancel: 'Cancel',
      save: 'Save',
      mustChange: 'must change password',
    },
    roles: { admin: 'Administrator', writer_all: 'Editor', reader_all: 'Reader', auditor: 'Auditor' },
    audit: {
      title: 'Audit Logs',
      subtitle: 'Record of every action in the portal.',
      when: 'When',
      actor: 'Actor',
      action: 'Action',
      entity: 'Entity',
      ip: 'IP',
      detail: 'Detail',
      allActions: 'All actions',
      empty: 'No records.',
    },
    rvs: {
      title: 'RVS Queue',
      subtitle: 'Dispatched vulnerabilities waiting for an RVS id.',
      rvsId: 'RVS id',
      enter: 'Register',
      placeholder: 'e.g. RVS-2026-001',
      empty: 'No vulnerabilities waiting for an RVS id.',
      dispatchedAt: 'Dispatched at',
    },
    actions: { dispatch: 'Dispatch' },
    apiKeys: {
      title: 'API Keys',
      subtitle: 'Keys for machine-to-machine integrations (scanners, pipelines).',
      newKey: 'New key',
      label: 'Label',
      role: 'Role',
      prefix: 'Prefix',
      created: 'Created',
      status: 'Status',
      active: 'Active',
      revoked: 'Revoked',
      revoke: 'Revoke',
      create: 'Create',
      cancel: 'Cancel',
      empty: 'No API keys.',
      copyWarn: 'Copy the key now — it will not be shown again.',
      copy: 'Copy',
      copied: 'Copied!',
      done: 'Done',
    },
    common: { prev: 'Previous', next: 'Next', close: 'Close', clear: 'Clear', help: 'Help', rowMenu: 'Actions' },
    profile: {
      menu: 'Profile',
      language: 'Language',
      title: 'My profile',
      placeholder: 'Profile page under construction.',
      username: 'Username',
      role: 'Role',
    },
    signOut: 'Sign out',
    comingSoon: 'Coming soon',
  },
}

export const LOCALES = [
  { code: 'pt-BR', label: 'Português (BR)', short: 'PT-BR' },
  { code: 'en', label: 'English', short: 'EN' },
]

function initialLocale() {
  try {
    const saved = localStorage.getItem('locale')
    if (saved && messages[saved]) return saved
  } catch { /* storage unavailable */ }
  return 'pt-BR'
}

export const locale = ref(initialLocale())
document.documentElement.lang = locale.value

export function setLocale(code) {
  if (!messages[code]) return
  locale.value = code
  document.documentElement.lang = code
  try { localStorage.setItem('locale', code) } catch { /* ignore */ }
}

function lookup(lang, parts) {
  let node = messages[lang]
  for (const p of parts) {
    node = node?.[p]
    if (node === undefined) return undefined
  }
  return node
}

// Falls back to pt-BR (the source language) before giving up and echoing the key.
export function t(path) {
  const parts = path.split('.')
  return lookup(locale.value, parts) ?? lookup('pt-BR', parts) ?? path
}
