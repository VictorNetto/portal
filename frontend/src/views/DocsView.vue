<script setup>
// User documentation: sections with subsections, a table of contents on the
// left and one card per subsection. Topics about features the user's role can't
// use are left out, like the nav does.
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import MarkdownView from '../components/MarkdownView.vue'
import { useAuthStore } from '../stores/auth'
import { DOCS } from '../docs'
import { locale, t } from '../i18n'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const allowed = (x) => !x.roles || x.roles.includes(auth.user?.role)
const sections = computed(() => (DOCS[locale.value] || DOCS['pt-BR'])
  .filter(allowed)
  .map((s) => ({ ...s, subs: s.subs.filter(allowed) }))
  .filter((s) => s.subs.length))
const current = ref('')

function go(id) {
  document.getElementById(`doc-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const sec = sections.value.find((s) => s.id === id)
  current.value = sec ? sec.subs[0].id : id
  router.replace({ hash: `#${id}` })
}

// Highlight the subsection being read: the top-most card in the upper part of
// the page. The observer only reports changes, so keep the whole visible set.
let observer = null
const visible = new Set()
function observe() {
  observer?.disconnect()
  visible.clear()
  observer = new IntersectionObserver((entries) => {
    for (const e of entries) e.isIntersecting ? visible.add(e.target) : visible.delete(e.target)
    const top = [...visible].sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0]
    if (top) current.value = top.dataset.id
  }, { root: document.querySelector('.main'), rootMargin: '0px 0px -70% 0px' })
  document.querySelectorAll('.docCard').forEach((el) => observer.observe(el))
}

onMounted(async () => {
  document.documentElement.removeAttribute('data-entity')
  await nextTick()
  observe()
  const id = route.hash.slice(1)
  if (id) document.getElementById(`doc-${id}`)?.scrollIntoView({ block: 'start' })
  const sec = sections.value.find((s) => s.id === id)
  current.value = sec ? sec.subs[0].id : id || sections.value[0]?.subs[0]?.id || ''
})
watch(sections, async () => { await nextTick(); observe() })
onUnmounted(() => observer?.disconnect())
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('docs.title') }}</h1>
        <p>{{ t('docs.subtitle') }}</p>
      </div>
    </div>

    <div class="docs">
      <nav class="toc" :aria-label="t('docs.contents')">
        <div class="tocLabel">{{ t('docs.contents') }}</div>
        <template v-for="s in sections" :key="s.id">
          <a :href="`#${s.id}`" class="tocSection" @click.prevent="go(s.id)">{{ s.title }}</a>
          <a v-for="x in s.subs" :key="x.id" :href="`#${x.id}`" class="tocItem"
             :class="{ current: current === x.id }" @click.prevent="go(x.id)">{{ x.title }}</a>
        </template>
      </nav>

      <div class="sections">
        <section v-for="s in sections" :id="`doc-${s.id}`" :key="s.id" class="docSection">
          <h2 class="secHead">{{ s.title }}</h2>
          <article v-for="x in s.subs" :id="`doc-${x.id}`" :key="x.id" :data-id="x.id" class="panel docCard">
            <h3>{{ x.title }}</h3>
            <MarkdownView :source="x.md" />
          </article>
        </section>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.docs { display: grid; grid-template-columns: 230px minmax(0, 860px); gap: 24px; align-items: start; }
.toc {
  position: sticky; top: 0; display: flex; flex-direction: column; gap: 1px;
  max-height: calc(100vh - var(--header) - 56px); overflow-y: auto;
}
.tocLabel { font-size: 11px; color: var(--dim); padding: 0 10px 6px; }
.tocSection {
  margin-top: 10px; padding: 5px 10px; font-size: 13px; font-weight: 500; color: var(--text);
  text-decoration: none; cursor: pointer; border-radius: var(--radius-sm);
}
.tocSection:first-of-type { margin-top: 0; }
.tocItem {
  padding: 5px 10px 5px 20px; border-radius: var(--radius-sm); font-size: 13px; color: var(--text-2);
  text-decoration: none; cursor: pointer;
}
.tocSection:hover, .tocItem:hover:not(.current) { background: var(--hover); }
.tocItem.current { color: var(--accent); }
.sections { display: grid; gap: 28px; }
.docSection { display: grid; gap: 12px; scroll-margin-top: 8px; }
.secHead { margin: 0; font-size: 19px; font-weight: 300; color: var(--text); }
.docCard { padding: 16px 20px 8px; scroll-margin-top: 8px; }
.docCard h3 { margin: 0 0 10px; font-size: 15px; font-weight: 400; color: var(--text); }
.docCard :deep(.mdView) { font-size: 14px; }
@media (max-width: 900px) {
  .docs { grid-template-columns: 1fr; }
  .toc { position: static; max-height: none; }
}
</style>
