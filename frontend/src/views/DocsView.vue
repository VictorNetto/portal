<script setup>
// User documentation: a table of contents and one card per topic. Topics about
// features the user's role can't use are left out, like the nav does.
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

const sections = computed(() => (DOCS[locale.value] || DOCS['pt-BR'])
  .filter((s) => !s.roles || s.roles.includes(auth.user?.role)))
const current = ref('')

function go(id) {
  document.getElementById(`doc-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  current.value = id
  router.replace({ hash: `#${id}` })
}

// Highlight the topic being read as the page scrolls.
let observer = null
function observe() {
  observer?.disconnect()
  observer = new IntersectionObserver((entries) => {
    const seen = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
    if (seen.length) current.value = seen[0].target.dataset.id
  }, { root: document.querySelector('.main'), rootMargin: '0px 0px -70% 0px' })
  document.querySelectorAll('.docCard').forEach((el) => observer.observe(el))
}

onMounted(async () => {
  document.documentElement.removeAttribute('data-entity')
  await nextTick()
  observe()
  const id = route.hash.slice(1)
  if (id) document.getElementById(`doc-${id}`)?.scrollIntoView({ block: 'start' })
  current.value = id || sections.value[0]?.id || ''
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
        <a v-for="s in sections" :key="s.id" :href="`#${s.id}`" class="tocItem"
           :class="{ current: current === s.id }" @click.prevent="go(s.id)">{{ s.title }}</a>
      </nav>

      <div class="cards">
        <section v-for="s in sections" :id="`doc-${s.id}`" :key="s.id" :data-id="s.id" class="panel docCard">
          <h2>{{ s.title }}</h2>
          <MarkdownView :source="s.md" />
        </section>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.docs { display: grid; grid-template-columns: 210px minmax(0, 860px); gap: 24px; align-items: start; }
.toc { position: sticky; top: 0; display: flex; flex-direction: column; gap: 1px; }
.tocLabel { font-size: 11px; color: var(--dim); padding: 0 10px 6px; }
.tocItem {
  padding: 6px 10px; border-radius: var(--radius-sm); font-size: 13px; color: var(--text-2);
  text-decoration: none; cursor: pointer;
}
.tocItem:hover:not(.current) { background: var(--hover); }
.tocItem.current { color: var(--accent); }
.cards { display: grid; gap: 16px; }
.docCard { padding: 16px 20px 8px; scroll-margin-top: 8px; }
.docCard h2 { margin: 0 0 10px; font-size: 15px; font-weight: 400; color: var(--text); }
.docCard :deep(.mdView) { font-size: 14px; }
@media (max-width: 900px) {
  .docs { grid-template-columns: 1fr; }
  .toc { position: static; flex-direction: row; flex-wrap: wrap; }
  .tocLabel { width: 100%; }
}
</style>
