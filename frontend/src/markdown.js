// Small, safe Markdown -> HTML renderer for the editor preview.
//
// Safety model: ALL input is HTML-escaped first, so no markup from the author
// can reach the DOM. Only the tags generated here exist in the output. Link and
// image targets are additionally restricted to an allowlist of URL shapes (the
// prototype let any href through, which would allow `[x](javascript:...)`).
//
// Supported: # ## ### headings, **bold**, *italic*, `code`, ``` fences,
// - / 1. lists, > quotes, [text](url), ![alt](url).

const ATTACHMENT_URL = /^\/api\/attachments\/([0-9a-f-]{36})\/content$/i
const SAFE_LINK = /^(https?:\/\/|mailto:|#)/i

export const attachmentPath = (id) => `/api/attachments/${id}/content`

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]))
}

// `url` arrives already HTML-escaped; unescape only to run the allowlist check.
function unescapeUrl(u) {
  return u.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
}

function inline(text) {
  const stash = []
  const keep = (html) => { stash.push(html); return `\u0000${stash.length - 1}\u0000` }

  // Code spans first, so nothing inside them is formatted.
  let out = text.replace(/`([^`]+)`/g, (_, c) => keep(`<code>${c}</code>`))

  // Images, then links. Disallowed targets are kept as plain text.
  out = out.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, alt, url) => {
    const raw = unescapeUrl(url)
    const att = raw.match(ATTACHMENT_URL)
    if (att) return keep(`<img alt="${alt}" data-att="${att[1]}">`)
    if (/^https?:\/\//i.test(raw)) {
      return keep(`<img alt="${alt}" src="${url}" referrerpolicy="no-referrer" loading="lazy">`)
    }
    return m
  })
  out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, label, url) => {
    const raw = unescapeUrl(url)
    if (SAFE_LINK.test(raw)) {
      return keep(`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`)
    }
    return m
  })

  out = out
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')

  return out.replace(/\u0000(\d+)\u0000/g, (_, i) => stash[Number(i)])
}

export function renderMarkdown(source) {
  const text = escapeHtml(source || '').replace(/\r\n?/g, '\n')

  // Fenced code blocks are lifted out so their content is never formatted.
  const blocks = []
  const withoutFences = text.replace(/```[^\n]*\n?([\s\S]*?)```/g, (_, code) => {
    blocks.push(`<pre><code>${code.replace(/\n$/, '')}</code></pre>`)
    return `\n\u0001${blocks.length - 1}\u0001\n`
  })

  const html = []
  const lines = withoutFences.split('\n')
  let para = []
  let list = null // { tag: 'ul' | 'ol', items: [] }
  let quote = []

  const flushPara = () => { if (para.length) { html.push(`<p>${para.join('<br>')}</p>`); para = [] } }
  const flushList = () => {
    if (list) { html.push(`<${list.tag}>${list.items.map((i) => `<li>${i}</li>`).join('')}</${list.tag}>`); list = null }
  }
  const flushQuote = () => {
    if (quote.length) { html.push(`<blockquote>${quote.join('<br>')}</blockquote>`); quote = [] }
  }
  const flushAll = () => { flushPara(); flushList(); flushQuote() }

  for (const line of lines) {
    let m
    if (!line.trim()) { flushAll(); continue }
    if ((m = line.match(/^\u0001(\d+)\u0001$/))) { flushAll(); html.push(blocks[Number(m[1])]); continue }
    if ((m = line.match(/^(#{1,3}) (.*)$/))) { flushAll(); html.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); continue }
    if ((m = line.match(/^&gt; ?(.*)$/))) { flushPara(); flushList(); quote.push(inline(m[1])); continue }
    if ((m = line.match(/^[-*] (.*)$/))) {
      flushPara(); flushQuote()
      if (!list || list.tag !== 'ul') { flushList(); list = { tag: 'ul', items: [] } }
      list.items.push(inline(m[1])); continue
    }
    if ((m = line.match(/^\d+\. (.*)$/))) {
      flushPara(); flushQuote()
      if (!list || list.tag !== 'ol') { flushList(); list = { tag: 'ol', items: [] } }
      list.items.push(inline(m[1])); continue
    }
    flushList(); flushQuote()
    para.push(inline(line))
  }
  flushAll()
  return html.join('')
}
