<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchAudit, auditFacets, ApiError } from '../api'
import { t } from '../i18n'
import { useAuthStore } from '../stores/auth'
import AppShell from '../components/AppShell.vue'
import FilterBar from '../components/FilterBar.vue'
import { AUDIT_FILTER_KEYS, parseAuditQuery } from '../auditQuery'
import { fmtDateTime } from '../dates'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const PAGE_SIZE = 50
const data = ref({ items: [], total: 0, page: 1, page_size: PAGE_SIZE })
const loading = ref(true)
const error = ref('')
const facets = ref({ actors: [], entity_types: [] })
const dynamicValues = computed(() => ({ actor: facets.value.actors, entity: facets.value.entity_types }))

// The query and the page live in the URL (/audit-logs?q=…&page=2), so a search can be shared.
const query = ref(String(route.query.q || ''))
const page = ref(Math.max(1, Number(route.query.page) || 1))
const parsed = computed(() => parseAuditQuery(query.value))
const pageCount = computed(() => Math.max(1, Math.ceil(data.value.total / PAGE_SIZE)))
const expanded = ref(null)
const filterBar = ref(null)

let seq = 0
async function load() {
  const mine = ++seq
  loading.value = true; error.value = ''
  try {
    const res = await searchAudit({ filters: parsed.value.filters, page: page.value, page_size: PAGE_SIZE })
    if (mine === seq) data.value = res
  } catch (e) {
    if (mine === seq) error.value = e instanceof ApiError ? (typeof e.detail === 'string' ? e.detail : t('errors.load')) : t('errors.load')
  } finally {
    if (mine === seq) loading.value = false
  }
}

function syncUrl() {
  const q = {}
  if (query.value.trim()) q.q = query.value
  if (page.value > 1) q.page = String(page.value)
  router.replace({ path: '/audit-logs', query: q })
}

// Typing searches after a short pause; only a change in the usable filters reloads.
let timer = null
const filtersKey = computed(() => JSON.stringify(parsed.value.filters))
watch(filtersKey, () => {
  clearTimeout(timer)
  timer = setTimeout(() => { page.value = 1; expanded.value = null; syncUrl(); load() }, 300)
})
watch(query, () => { clearTimeout(urlTimer); urlTimer = setTimeout(syncUrl, 300) })
let urlTimer = null

function go(n) { page.value = n; expanded.value = null; syncUrl(); load() }

// Clicking a value narrows the search by it.
function addFilter(key, value) {
  const v = /\s/.test(value) ? `"${value}"` : value
  const tok = `${key}:${v}`
  const cur = query.value.trim()
  if (cur.split(/\s+/).includes(tok)) return
  query.value = cur ? `${cur} ${tok}` : tok
}

// Where a record opens, when this user can open it.
function recordLink(e) {
  if (!e.entity_id) return null
  if (e.entity_type === 'vulnerability') return `/vulnerabilities/${e.entity_id}`
  if (e.entity_type === 'report') return `/reports/${e.entity_id}`
  if (e.entity_type === 'user' && isAdmin.value) return `/users?user=${e.entity_id}`
  if (e.entity_type === 'dashboard' && isAdmin.value) return `/dashboards/${e.entity_id}`
  return null
}
const recordToken = (e) => e.entity_label && /^[A-Z]+-\d+/.test(e.entity_label) ? e.entity_label : e.entity_id

const kindLabel = (k) => { const s = t('audit.kinds.' + k); return s.startsWith('audit.') ? k : s }

function fmtDetail(d) {
  if (!d) return '—'
  return Object.entries(d).map(([k, v]) =>
    `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join('  ')
}
const detailLines = (d) => Object.entries(d || {}).map(([k, v]) =>
  [k, typeof v === 'object' && v !== null ? JSON.stringify(v, null, 2) : String(v)])

// Color actions by rough category for quick scanning.
const actionClass = (a) => {
  if (['delete', 'api_key_revoke', 'login_failed'].includes(a)) return 'danger'
  if (['create', 'api_key_create', 'send', 'accept'].includes(a)) return 'good'
  if (['permission_change', 'correction', 'lock_override', 'status_change'].includes(a)) return 'warn'
  return 'neutral'
}

function onKeydown(e) {
  const tag = e.target.tagName
  const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable
  if (e.key === '/' && !typing) { e.preventDefault(); filterBar.value?.focusAndTrigger() }
}

onMounted(async () => {
  document.documentElement.removeAttribute('data-entity')
  window.addEventListener('keydown', onKeydown)
  load()
  try { facets.value = await auditFacets() } catch { /* the menus just stay empty */ }
})
onUnmounted(() => { window.removeEventListener('keydown', onKeydown); clearTimeout(timer); clearTimeout(urlTimer) })
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('audit.title') }}</h1>
        <p>{{ t('audit.subtitle') }}</p>
      </div>
    </div>

    <div class="toolbar">
      <FilterBar ref="filterBar" v-model="query" class="auditFilter" :keys="AUDIT_FILTER_KEYS"
                 :dynamic-values="dynamicValues" help="filter.auditHelp" />
      <span class="count mono">{{ data.total }} {{ t('misc.records') }}</span>
    </div>
    <p v-if="parsed.invalid.length" class="ignored">{{ t('audit.ignored', { tokens: parsed.invalid.join(' ') }) }}</p>

    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel" :class="{ busy: loading }">
      <table>
        <thead>
          <tr>
            <th style="width:190px">{{ t('audit.when') }}</th>
            <th style="width:170px">{{ t('audit.actor') }}</th>
            <th style="width:150px">{{ t('audit.action') }}</th>
            <th style="width:230px">{{ t('audit.entity') }}</th>
            <th style="width:120px">{{ t('audit.ip') }}</th>
            <th>{{ t('audit.detail') }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="e in data.items" :key="e.id">
            <tr class="row" :class="{ open: expanded === e.id }" @click="expanded = expanded === e.id ? null : e.id">
              <td class="mono dim">{{ fmtDateTime(e.created_at) }}</td>
              <td class="actor">
                <button class="val" :title="t('audit.filterBy')" @click.stop="addFilter('actor', e.actor)">{{ e.actor }}</button>
                <small v-if="e.actor_name" class="dim name">{{ e.actor_name }}</small>
              </td>
              <td><button class="val act" :class="actionClass(e.action)" :title="t('audit.filterBy')"
                          @click.stop="addFilter('action', e.action)">{{ e.action }}</button></td>
              <td>
                <template v-if="e.entity_type">
                  <button class="val dim" :title="t('audit.filterBy')" @click.stop="addFilter('entity', e.entity_type)">{{ kindLabel(e.entity_type) }}</button>
                  <button v-if="e.entity_id" class="val label" :title="t('audit.filterBy')"
                          @click.stop="addFilter('record', recordToken(e))">{{ e.entity_label || e.entity_id.slice(0, 8) }}</button>
                </template>
                <span v-else class="dim">—</span>
              </td>
              <td class="mono dim">
                <button v-if="e.ip_address" class="val mono" :title="t('audit.filterBy')" @click.stop="addFilter('ip', e.ip_address)">{{ e.ip_address }}</button>
                <span v-else>—</span>
              </td>
              <td class="mono detail">{{ fmtDetail(e.detail) }}</td>
            </tr>
            <tr v-if="expanded === e.id" class="more">
              <td colspan="6">
                <dl class="facts">
                  <template v-if="e.entity_id">
                    <dt>{{ t('audit.record') }}</dt>
                    <dd>
                      <span class="mono">{{ e.entity_id }}</span>
                      <RouterLink v-if="recordLink(e)" :to="recordLink(e)" class="open">{{ t('audit.open') }}</RouterLink>
                    </dd>
                  </template>
                  <template v-for="[k, v] in detailLines(e.detail)" :key="k">
                    <dt class="mono">{{ k }}</dt><dd><pre>{{ v }}</pre></dd>
                  </template>
                  <template v-if="!e.detail && !e.entity_id"><dt>{{ t('audit.detail') }}</dt><dd>—</dd></template>
                </dl>
              </td>
            </tr>
          </template>
          <tr v-if="!loading && !data.items.length"><td colspan="6" class="empty">{{ t('audit.empty') }}</td></tr>
        </tbody>
      </table>
    </section>

    <div class="pagination">
      <span class="pageInfo mono">{{ data.total }} {{ t('misc.records') }}</span>
      <button class="pageBtn" :disabled="page <= 1" @click="go(page - 1)">{{ t('common.prev') }}</button>
      <span class="pageInfo mono">{{ page }} / {{ pageCount }}</span>
      <button class="pageBtn" :disabled="page >= pageCount" @click="go(page + 1)">{{ t('common.next') }}</button>
    </div>
  </AppShell>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.auditFilter { flex: 1; max-width: 760px; }
.count { color: var(--muted); font-size: 12px; white-space: nowrap; }
.ignored { margin: -4px 0 10px; color: var(--muted); font-size: 12px; }
.busy { opacity: .6; transition: opacity .15s; }
table { table-layout: fixed; }
td { padding: 9px 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12.5px; }
th { padding: 10px 14px; }
.row { cursor: pointer; }
.row:hover, .row.open { background: var(--hover); }
.dim { color: var(--muted); }
.actor { color: var(--text); }
.name { margin-left: 6px; }
.val { border: 0; background: transparent; padding: 0; font: inherit; color: inherit; cursor: pointer; }
.val:hover { text-decoration: underline; }
.val.label { margin-left: 6px; color: var(--text); }
.act { font-size: 11px; padding: 2px 8px; border-radius: var(--radius-sm); font-family: var(--mono); }
.act:hover { text-decoration: none; filter: brightness(.96); }
.act.neutral { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.act.good { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }
.act.warn { color: var(--st-wait-fg); background: var(--st-wait-bg); }
.act.danger { color: var(--danger); background: var(--danger-soft); }
.more td { white-space: normal; background: var(--panel-2); padding: 12px 18px; }
.facts { display: grid; grid-template-columns: 160px 1fr; gap: 6px 14px; margin: 0; font-size: 12.5px; }
.facts dt { color: var(--muted); }
.facts dd { margin: 0; min-width: 0; }
.facts pre { margin: 0; font-family: var(--mono); font-size: 12px; white-space: pre-wrap; word-break: break-word; }
.open { margin-left: 10px; font-size: 12px; color: var(--accent); text-decoration: none; }
.open:hover { text-decoration: underline; }
</style>
