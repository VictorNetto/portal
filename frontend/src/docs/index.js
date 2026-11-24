// The user guide (/docs), organised like a book: chapters, each with an opening page and its
// sections, one page each, read in order with Previous / Next.
//
// The text is Markdown, one file per chapter and language (pt/, en/). A page starts at a line
// `<!-- page: <id> -->`, and its first `# ` line is its title. Links between pages are written
// `[text](#<id>)`. This file only decides the order and who sees what: a chapter or page with
// `roles` is shown only to those roles; without, it is the red team's, so a defense (D17) or
// dashboard (D18) account doesn't see it.

const CREATORS = ['admin', 'write_all', 'write_restricted']
const AUDIT = ['auditor', 'admin']
// The defense team's guide; admins see it too, to know what that team sees.
const DEFENSE = ['defense', 'admin']
const DASHBOARD = ['dashboard', 'admin']

export const BOOK = [
  { id: 'introducao', unnumbered: true },
  { id: 'primeiros-passos', pages: ['inicio', 'sessao', 'perfil', 'papeis'] },
  { id: 'vulnerabilidades', pages: ['vuln-criar', 'textos', 'vuln-ciclo', 'vuln-apos', 'vuln-conflitos'] },
  { id: 'relatorios', pages: ['rel-criar', 'rel-conteudo', 'rel-envio'] },
  { id: 'templates', roles: CREATORS, pages: ['tpl-salvar', 'tpl-compartilhar'] },
  { id: 'operacoes', pages: ['filtros', 'filtros-datas', 'exportar'] },
  { id: 'auditoria', roles: AUDIT, pages: ['auditoria-filtros'] },
  {
    id: 'api', roles: CREATORS,
    pages: ['api-chaves', 'api-convencoes', 'api-ler', 'api-criar', 'api-lotes', 'api-importar',
      'api-rvs', 'api-relatorios', 'api-erros'],
  },
  { id: 'dashboards', roles: DASHBOARD, pages: ['dash-consultas', 'dash-exemplos', 'dash-variaveis', 'dash-tv'] },
  { id: 'gerenciamento', roles: ['admin'], pages: ['adm-usuarios', 'adm-chaves', 'adm-templates', 'adm-reservas'] },
  {
    id: 'defesa', roles: DEFENSE,
    pages: ['def-sessao', 'def-secoes', 'def-aceitar', 'def-risco', 'def-lote', 'def-filtros', 'def-depois'],
  },
]

// Ids of the earlier one-page guide (/docs#<id>), so old links still land on the right page.
export const ALIASES = {
  geral: 'primeiros-passos', identificadores: 'vulnerabilidades', 'filtros-avancados': 'filtros-datas',
  rvs: 'vuln-apos', 'rel-editar': 'rel-criar', 'api-visao': 'api', 'api-auth': 'api-chaves',
  'api-ep-vulns': 'api-ler', 'api-ep-vuln': 'api-ler', 'api-ep-vuln-atts': 'api-ler', 'api-ep-att': 'api-ler',
  'api-ep-vuln-export': 'api-ler', 'api-editar': 'api-criar', 'api-ep-rvsq': 'api-rvs', 'api-ep-rvs': 'api-rvs',
  'api-ep-reports': 'api-relatorios', 'api-ep-report': 'api-relatorios', 'api-ep-report-export': 'api-relatorios',
  'api-ep-health': 'api-erros', 'api-praticas': 'api-erros', 'adm-acesso': 'adm-usuarios',
  'adm-auditoria': 'auditoria', 'def-inicio': 'defesa', 'def-vuln': 'def-secoes', 'def-registro': 'defesa',
  'dash-inicio': 'dashboards',
}

const FILES = {
  'pt-BR': import.meta.glob('./pt/*.md', { query: '?raw', import: 'default', eager: true }),
  en: import.meta.glob('./en/*.md', { query: '?raw', import: 'default', eager: true }),
}

function parse(files) {
  const pages = {}
  for (const text of Object.values(files)) {
    // split with a capture group: [before, id1, body1, id2, body2, ...]
    const parts = text.replace(/\r\n?/g, '\n').split(/^<!-- page: ([\w-]+) -->[ \t]*$/m)
    for (let i = 1; i < parts.length; i += 2) {
      const body = parts[i + 1].trim()
      const m = body.match(/^# (.+)\n?/)
      pages[parts[i]] = { title: m ? m[1].trim() : parts[i], md: m ? body.slice(m[0].length).trim() : body }
    }
  }
  return pages
}

const PARSED = Object.fromEntries(Object.entries(FILES).map(([lang, files]) => [lang, parse(files)]))

const allowed = (roles, role) => (roles ? roles.includes(role) : !['defense', 'dashboard'].includes(role))

// The book one user reads: the chapters and pages their role may see, numbered in that order,
// and the same pages flat, in reading order (each chapter's opening page, then its sections).
export function bookFor(lang, role) {
  const text = PARSED[lang] || PARSED['pt-BR']
  const page = (id) => text[id] || PARSED['pt-BR'][id]
  const chapters = []
  let n = 0
  for (const ch of BOOK) {
    if (!allowed(ch.roles, role) || !page(ch.id)) continue
    const num = ch.unnumbered ? '' : String(++n)
    const chapter = { id: ch.id, num, ...page(ch.id), chapter: true, pages: [] }
    chapter.pages = (ch.pages || []).filter(page).map((id, i) => ({
      id, num: num ? `${num}.${i + 1}` : '', ...page(id), parent: chapter,
    }))
    chapters.push(chapter)
  }
  const flat = chapters.flatMap((c) => [c, ...c.pages])
  return { chapters, flat, byId: Object.fromEntries(flat.map((p) => [p.id, p])) }
}

// Search: every word must appear in the page's title or text (case and accents ignored).
const fold = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
const plain = (md) => md.replace(/```[\s\S]*?```/g, ' ').replace(/[`*#>|[\]]/g, '').replace(/\(#[\w-]+\)/g, '')

export function search(book, query) {
  const words = fold(query).split(/\s+/).filter(Boolean)
  if (!words.length) return []
  const hits = []
  for (const p of book.flat) {
    const text = plain(p.md)
    const hay = fold(`${p.title} ${text}`)
    if (!words.every((w) => hay.includes(w))) continue
    const folded = fold(text)
    const at = Math.max(0, folded.indexOf(words[0]))
    const start = Math.max(0, at - 60)
    const snippet = (start ? '…' : '') + text.slice(start, at + 140).replace(/\s+/g, ' ').trim() + '…'
    hits.push({ page: p, snippet, inTitle: fold(p.title).includes(words[0]) })
  }
  return hits.sort((a, b) => b.inTitle - a.inTitle)
}
