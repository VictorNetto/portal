<script setup>
// The user guide, read like a book: the chapters and their sections on the left, one page at a
// time on the right, Previous / Next at the bottom (and the ← → keys). /docs/<page> is a page;
// /docs and the old one-page anchors (/docs#<id>) land on the right one. Pages about what the
// user's role can't use are left out, like the nav does (docs/index.js).
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import MarkdownView from '../components/MarkdownView.vue'
import { useAuthStore } from '../stores/auth'
import { ALIASES, bookFor, search } from '../docs/index.js'
import { locale, t } from '../i18n'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const book = computed(() => bookFor(locale.value, auth.user?.role))
const pageId = computed(() => String(route.params.page || ''))
const page = computed(() => book.value.byId[pageId.value] || null)
const index = computed(() => book.value.flat.indexOf(page.value))
const prev = computed(() => (index.value > 0 ? book.value.flat[index.value - 1] : null))
const next = computed(() => (index.value >= 0 ? book.value.flat[index.value + 1] || null : null))
const chapter = computed(() => page.value && (page.value.chapter ? page.value : page.value.parent))

const to = (id) => ({ name: 'docs', params: { page: id } })
const label = (p) => (p.num ? `${p.num}. ${p.title}` : p.title)

// An unknown, old or hidden page id goes to the page it became, or to the first page.
function settle() {
  const want = pageId.value || route.hash.slice(1)
  const { byId, flat } = book.value
  const id = byId[want] ? want : byId[ALIASES[want]] ? ALIASES[want] : flat[0]?.id
  if (id && (id !== pageId.value || route.hash)) router.replace(to(id))
}
watch([pageId, book], settle, { immediate: true })

const scroller = () => document.querySelector('.main')
watch(pageId, async () => { query.value = ''; await nextTick(); scroller()?.scrollTo({ top: 0 }) })

// Links between pages are written [text](#id): open them here instead of in a new tab.
function onArticleClick(e) {
  const a = e.target.closest('a')
  const href = a?.getAttribute('href') || ''
  if (!href.startsWith('#')) return
  e.preventDefault()
  router.push(to(href.slice(1)))
}

// ← and → turn the page, unless the user is typing.
function onKey(e) {
  if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return
  if (e.target.closest?.('input, textarea, select, [contenteditable="true"]')) return
  const target = e.key === 'ArrowLeft' ? prev.value : e.key === 'ArrowRight' ? next.value : null
  if (target) { e.preventDefault(); router.push(to(target.id)) }
}
onMounted(() => {
  document.documentElement.removeAttribute('data-entity')
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => window.removeEventListener('keydown', onKey))

const query = ref('')
const hits = computed(() => search(book.value, query.value).slice(0, 30))
function openHit(id) { query.value = ''; router.push(to(id)) }
</script>

<template>
  <AppShell>
    <div class="book">
      <nav class="toc" :aria-label="t('docs.contents')">
        <div class="tocTitle">{{ t('docs.title') }}</div>
        <input v-model="query" class="search" type="search" :placeholder="t('docs.search')" :aria-label="t('docs.search')" />
        <ol class="chapters">
          <li v-for="c in book.chapters" :key="c.id">
            <router-link :to="to(c.id)" class="tocLink chapterLink" :class="{ current: c.id === pageId }">
              <span v-if="c.num" class="num">{{ c.num }}.</span>{{ c.title }}
            </router-link>
            <ol v-if="c.pages.length" class="sections">
              <li v-for="p in c.pages" :key="p.id">
                <router-link :to="to(p.id)" class="tocLink" :class="{ current: p.id === pageId }">
                  <span class="num">{{ p.num }}.</span>{{ p.title }}
                </router-link>
              </li>
            </ol>
          </li>
        </ol>
      </nav>

      <div class="reader">
        <section v-if="query.trim()" class="results" aria-live="polite">
          <p class="eyebrow">{{ hits.length ? t('docs.results', { n: hits.length }) : t('docs.noResults') }}</p>
          <button v-for="h in hits" :key="h.page.id" type="button" class="hit" @click="openHit(h.page.id)">
            <span class="hitTitle">{{ label(h.page) }}</span>
            <span v-if="!h.page.chapter" class="hitWhere">{{ label(h.page.parent) }}</span>
            <span class="hitText">{{ h.snippet }}</span>
          </button>
        </section>

        <article v-else-if="page" class="page" @click="onArticleClick">
          <p v-if="page.num" class="eyebrow">
            {{ page.chapter ? t('docs.chapter', { n: page.num }) : label(chapter) }}
          </p>
          <h1>{{ page.title }}</h1>
          <MarkdownView class="prose" :source="page.md" tables />

          <nav v-if="page.chapter && page.pages.length" class="inChapter" :aria-label="t('docs.inChapter')">
            <h2>{{ t('docs.inChapter') }}</h2>
            <ol>
              <li v-for="p in page.pages" :key="p.id">
                <router-link :to="to(p.id)"><span class="num">{{ p.num }}.</span>{{ p.title }}</router-link>
              </li>
            </ol>
          </nav>

          <nav class="pager" :aria-label="t('docs.pager')">
            <router-link v-if="prev" :to="to(prev.id)" class="turn prev" :title="t('docs.keys')">
              <span class="dir">← {{ t('docs.prev') }}</span><span class="where">{{ label(prev) }}</span>
            </router-link>
            <span v-else></span>
            <router-link v-if="next" :to="to(next.id)" class="turn next" :title="t('docs.keys')">
              <span class="dir">{{ t('docs.next') }} →</span><span class="where">{{ label(next) }}</span>
            </router-link>
          </nav>
        </article>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.book { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 40px; align-items: start; }

.toc {
  position: sticky; top: 0; max-height: calc(100vh - var(--header) - 48px); overflow-y: auto;
  padding-right: 8px; border-right: 1px solid var(--line);
}
.tocTitle { font-size: 13px; font-weight: 500; color: var(--text); padding: 2px 10px 10px; }
.search {
  width: calc(100% - 4px); margin: 0 2px 14px; padding: 6px 10px; font-size: 13px;
  border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--bg); color: var(--text);
}
.chapters, .sections { list-style: none; margin: 0; padding: 0; }
.chapters > li { margin-bottom: 6px; }
.tocLink {
  display: flex; gap: 6px; padding: 4px 10px; border-radius: var(--radius-sm);
  font-size: 13px; line-height: 1.4; color: var(--text-2); text-decoration: none;
}
.chapterLink { color: var(--text); font-weight: 500; }
.sections .tocLink { padding-left: 22px; }
.tocLink:hover:not(.current) { background: var(--hover); }
.tocLink.current { color: var(--accent); background: var(--hover); }
.num { color: var(--dim); font-variant-numeric: tabular-nums; flex: none; }
.tocLink.current .num { color: inherit; }

.reader { min-width: 0; }
.page, .results { max-width: 740px; padding: 8px 0 40px; }
.eyebrow { margin: 0 0 6px; font-size: 12px; letter-spacing: .02em; color: var(--dim); }
.page h1 { margin: 0 0 22px; font-size: 28px; font-weight: 300; line-height: 1.2; color: var(--text); }

.page .prose { font-size: 15px; line-height: 1.75; color: var(--text-2); }
.prose :deep(p) { margin: 0 0 16px; }
.prose :deep(h2) { margin: 34px 0 12px; font-size: 20px; font-weight: 400; color: var(--text); }
.prose :deep(h3) { margin: 24px 0 8px; font-size: 16px; font-weight: 500; color: var(--text); }
.prose :deep(ul), .prose :deep(ol) { margin: 0 0 16px 22px; }
.prose :deep(li) { margin-bottom: 4px; }
.prose :deep(strong) { color: var(--text); font-weight: 500; }
.prose :deep(code) { font-size: 13px; }
.prose :deep(pre) { margin: 0 0 18px; padding: 12px 14px; font-size: 13px; line-height: 1.55; }
.prose :deep(table) { width: 100%; margin: 4px 0 20px; border-collapse: collapse; font-size: 14px; line-height: 1.5; }
.prose :deep(th) { text-align: left; font-weight: 500; color: var(--text); border-bottom: 1px solid var(--line-2); padding: 6px 12px 6px 0; }
.prose :deep(td) { vertical-align: top; border-bottom: 1px solid var(--line); padding: 7px 12px 7px 0; }
.prose :deep(td:first-child) { white-space: nowrap; }

.inChapter { margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--line); }
.inChapter h2 { margin: 0 0 10px; font-size: 14px; font-weight: 500; color: var(--text); }
.inChapter ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.inChapter a { display: flex; gap: 8px; font-size: 14px; color: var(--accent); text-decoration: none; }
.inChapter a:hover { text-decoration: underline; }

.pager { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 40px; }
.turn {
  display: grid; gap: 3px; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius);
  text-decoration: none; color: var(--text);
}
.turn:hover { border-color: var(--accent); }
.turn.next { text-align: right; grid-column: 2; }
.dir { font-size: 12px; color: var(--dim); }
.where { font-size: 14px; color: var(--accent); }

.hit {
  display: grid; gap: 3px; width: 100%; text-align: left; padding: 12px 0; background: none; border: 0;
  border-bottom: 1px solid var(--line); cursor: pointer; color: var(--text-2); font: inherit;
}
.hit:hover .hitTitle { text-decoration: underline; }
.hitTitle { font-size: 15px; color: var(--accent); }
.hitWhere { font-size: 12px; color: var(--dim); }
.hitText { font-size: 13px; line-height: 1.5; }

@media (max-width: 900px) {
  .book { grid-template-columns: 1fr; gap: 16px; }
  .toc { position: static; max-height: none; border-right: 0; border-bottom: 1px solid var(--line); padding-bottom: 12px; }
}
</style>
