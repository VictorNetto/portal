<script setup>
// Report templates (D11). First version: find a template and read what it contains.
// Editing, renaming, deleting and sharing come next (see docs/BACKLOG.md).
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listReportTemplates, getReportTemplate, ApiError } from '../api'
import { useAuthStore } from '../stores/auth'
import { fmtDate, fmtDateTime } from '../dates'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'
import MarkdownView from '../components/MarkdownView.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const templates = ref([])
const loading = ref(true)
const error = ref('')

// --- list: search + "whose" filter ---------------------------------------------------
const q = ref('')
const scope = ref('')   // '' all | mine | global | others (admins only)
const scopeOf = (x) => (x.mine ? 'mine' : x.is_global ? 'global' : 'others')
const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return templates.value.filter((x) =>
    (!needle || x.name.toLowerCase().includes(needle) || x.owner.username.toLowerCase().includes(needle)) &&
    (!scope.value || scopeOf(x) === scope.value))
})

async function load() {
  loading.value = true; error.value = ''
  try { templates.value = await listReportTemplates() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

// --- selection (kept in the URL: /templates?template=<id>) -------------------------------
const selectedId = computed(() => route.query.template || null)
const select = (x) => router.replace({ path: '/templates', query: x ? { template: x.id } : {} })
const detail = ref(null)
const detailError = ref('')
async function loadDetail() {
  detail.value = null; detailError.value = ''
  if (!selectedId.value) return
  try { detail.value = await getReportTemplate(selectedId.value) }
  catch (e) { detailError.value = e instanceof ApiError ? e.detail : t('errors.load') }
}
watch(selectedId, loadDetail)

const availability = (x) => (x.is_global ? t('tpls.forAll') : t('tpls.onlyOwner'))

onMounted(async () => {
  document.documentElement.setAttribute('data-entity', 'reports') // templates belong to reports
  await load()
  loadDetail()
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('tpls.title') }}</h1>
        <p>{{ t('tpls.subtitle') }}</p>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="tplLayout" :class="{ withDetail: !!selectedId }">
      <div class="listCol">
        <div class="toolbar">
          <input v-model="q" class="search" :placeholder="t('tpls.search')" />
          <select v-model="scope" class="filterSel">
            <option value="">{{ t('tpls.allScopes') }}</option>
            <option value="mine">{{ t('tpl.group.mine') }}</option>
            <option value="global">{{ t('tpl.group.global') }}</option>
            <option v-if="isAdmin" value="others">{{ t('tpl.group.others') }}</option>
          </select>
          <span class="count mono">{{ filtered.length }} / {{ templates.length }}</span>
        </div>

        <section class="panel listPanel">
          <table class="ttable">
            <thead>
              <tr>
                <th>{{ t('tpls.name') }}</th>
                <th>{{ t('tpls.owner') }}</th>
                <th>{{ t('tpls.availability') }}</th>
                <th>{{ t('tpls.sections') }}</th>
                <th>{{ t('cols.updatedAt') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="x in filtered" :key="x.id" :class="{ sel: x.id === selectedId }" @click="select(x)">
                <td class="tname">{{ x.name }}</td>
                <td>{{ x.mine ? t('tpls.me') : x.owner.username }}</td>
                <td>{{ availability(x) }}</td>
                <td class="mono">{{ x.section_count }}</td>
                <td class="dateCell" :title="fmtDateTime(x.updated_at)">{{ fmtDate(x.updated_at) }}</td>
              </tr>
              <tr v-if="!loading && !filtered.length">
                <td colspan="5" class="empty">{{ templates.length ? '—' : t('tpls.empty') }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <aside v-if="selectedId" class="panel detail">
        <p v-if="detailError" class="err">{{ detailError }}</p>
        <template v-else-if="detail">
          <header class="dHead">
            <h2 class="dName">{{ detail.name }}</h2>
            <button class="btn" @click="select(null)">{{ t('common.close') }}</button>
          </header>
          <dl class="facts">
            <dt>{{ t('tpls.owner') }}</dt><dd>{{ detail.mine ? t('tpls.me') : detail.owner.username }}</dd>
            <dt>{{ t('tpls.availability') }}</dt><dd>{{ availability(detail) }}</dd>
            <dt>{{ t('tpls.createdAt') }}</dt><dd>{{ fmtDateTime(detail.created_at) }}</dd>
          </dl>

          <div class="content">
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.summary') }}</h3>
              <MarkdownView v-if="detail.executive_summary_md" :source="detail.executive_summary_md" />
              <p v-else class="muted">—</p>
            </section>
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.intro') }}</h3>
              <MarkdownView v-if="detail.introduction_md" :source="detail.introduction_md" />
              <p v-else class="muted">—</p>
            </section>
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.extras') }} ({{ detail.sections.length }})</h3>
              <div v-for="(s, i) in detail.sections" :key="i" class="extra">
                <h4 class="extraTitle">{{ s.title }}</h4>
                <MarkdownView v-if="s.content_markdown" :source="s.content_markdown" />
                <p v-else class="muted">—</p>
              </div>
              <p v-if="!detail.sections.length" class="muted">—</p>
            </section>
          </div>
        </template>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.tplLayout { display: grid; grid-template-columns: 1fr; gap: 16px; align-items: start; }
.tplLayout.withDetail { grid-template-columns: minmax(0, 1fr) minmax(420px, 1fr); }
@media (max-width: 1100px) { .tplLayout.withDetail { grid-template-columns: 1fr; } }

.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.search { flex: 1 1 200px; min-width: 160px; max-width: 320px; }
.filterSel { height: 32px; }
.count { color: var(--muted); font-size: 12px; margin-left: auto; }

.listPanel { overflow: auto; max-height: calc(100vh - 240px); }
.ttable tbody tr { cursor: pointer; }
.ttable tbody tr.sel { background: var(--accent-soft); }
.tname { color: var(--text); }
.dateCell { color: var(--muted); font-variant-numeric: tabular-nums; }
.empty { text-align: center; color: var(--muted); padding: 2rem; }

.detail { padding: 16px 18px 18px; position: sticky; top: 0; max-height: calc(100vh - 140px); overflow: auto; }
.dHead { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.dName { margin: 0; font-size: 18px; font-weight: 400; flex: 1; }
.facts { display: grid; grid-template-columns: 120px 1fr; gap: 6px 12px; margin: 0 0 14px; font-size: 13px; }
.facts dt { color: var(--muted); }
.facts dd { margin: 0; }
.content { border-top: 1px solid var(--line); padding-top: 12px; display: grid; gap: 16px; }
.blockTitle { margin: 0 0 8px; font-size: 14px; font-weight: 400; color: var(--text); }
.extra { margin: 0 0 12px; padding-left: 12px; border-left: 2px solid var(--line); }
.extraTitle { margin: 0 0 6px; font-size: 13px; font-weight: 500; color: var(--text-2); }
</style>
