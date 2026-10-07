<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { listVulns, deleteVuln, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'
import FilterBar from '../components/FilterBar.vue'
import { parseQuery } from '../filterQuery'

const router = useRouter()

// Entity switcher (§5.4). Reports tab is present but stubbed (no backend yet).
const entity = ref('vulns')

// Drive the global accent: reports -> indigo, vulns -> green. Sets a data
// attribute on <html> that [data-entity="reports"] in style.css keys off.
watch(entity, (e) => {
  document.documentElement.setAttribute('data-entity', e === 'reports' ? 'reports' : 'vulns')
}, { immediate: true })
onUnmounted(() => document.documentElement.removeAttribute('data-entity'))

const vulns = ref([])
const loading = ref(true)
const error = ref('')

// Selection (§5.10/§5.11) and preview (bottom panel, §5.9) are independent.
const selected = ref(new Set())
const preview = ref(null)

// Pagination (§5.12)
const pageSize = ref(50) // fixed; not user-selectable
const page = ref(1)

// Single-line filter/find (the FilterBar). "/" focuses it and opens the menu.
// Filter text is isolated per entity tab: switching tabs shows that tab's own
// filter, and switching back restores it.
const queries = ref({ vulns: '', reports: '' })
const query = computed({
  get: () => queries.value[entity.value],
  set: (v) => { queries.value[entity.value] = v },
})
const filterBar = ref(null)
watch(query, () => { page.value = 1 })

function onKeydown(e) {
  const tag = e.target.tagName
  const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable
  // Only hijack "/" when focus is outside an input; the filter bar handles its
  // own "/" while focused.
  if (e.key === '/' && !typing) {
    e.preventDefault()
    filterBar.value?.focusAndTrigger()
  }
}
// Close the row action menu on any click outside it.
function onDocClick(e) {
  if (menuFor.value && !e.target.closest('.rowActionWrap')) menuFor.value = null
}
onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onDocClick)
})

const filteredVulns = computed(() => {
  let rows = vulns.value
  if (query.value.trim()) {
    const { predicate } = parseQuery(query.value)
    rows = rows.filter(predicate)
  }
  return rows
})

// Distinct operator usernames across loaded vulns, for the operator: value
// menu. (Until operator assignment exists this is typically empty.)
const operatorValues = computed(() => {
  const set = new Set()
  for (const v of vulns.value) {
    const ops = Array.isArray(v.operators) ? v.operators : []
    for (const o of ops) {
      const name = typeof o === 'string' ? o : o?.username
      if (name) set.add(name)
    }
  }
  return [...set].sort()
})
const dynamicFilterValues = computed(() => ({ operator: operatorValues.value }))

async function load() {
  loading.value = true; error.value = ''
  try { vulns.value = await listVulns() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

const total = computed(() => filteredVulns.value.length)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredVulns.value.slice(start, start + pageSize.value)
})
const rangeLabel = computed(() => {
  if (!total.value) return `0 ${t('hub.of')} 0`
  const start = (page.value - 1) * pageSize.value + 1
  const end = Math.min(page.value * pageSize.value, total.value)
  return `${start}-${end} ${t('hub.of')} ${total.value}`
})

// Select-all with indeterminate state (§5.11)
const allChecked = computed(() =>
  pageRows.value.length > 0 && pageRows.value.every((v) => selected.value.has(v.id)))
const someChecked = computed(() =>
  pageRows.value.some((v) => selected.value.has(v.id)) && !allChecked.value)

function toggleAll(e) {
  const on = e.target.checked
  for (const v of pageRows.value) {
    if (on) selected.value.add(v.id)
    else selected.value.delete(v.id)
  }
  selected.value = new Set(selected.value)
}
function toggleRow(id) {
  if (selected.value.has(id)) selected.value.delete(id)
  else selected.value.add(id)
  selected.value = new Set(selected.value)
}

function openPreview(v) { preview.value = v }
function closePreview() { preview.value = null }

// Row action menu (§5.9 three-dots)
const menuFor = ref(null)
const menuPos = ref({})
function toggleMenu(id, ev) {
  if (menuFor.value === id) { menuFor.value = null; return }
  menuFor.value = id
  // The menu is position:fixed so the scrolling list can't clip it. Open it
  // below the button, or above when there isn't room below.
  const rect = ev.currentTarget.getBoundingClientRect()
  const right = window.innerWidth - rect.right
  menuPos.value = window.innerHeight - rect.bottom < 170
    ? { right: right + 'px', bottom: (window.innerHeight - rect.top + 4) + 'px' }
    : { right: right + 'px', top: (rect.bottom + 4) + 'px' }
}

function goDetail(id) { router.push(`/vulnerabilities/${id}`) }
function goCreate() { router.push('/vulnerabilities/new') }

async function removeRow(id) {
  menuFor.value = null
  if (!confirm(t('vuln.confirmDelete'))) return
  try { await deleteVuln(id); if (preview.value?.id === id) preview.value = null; await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

// CVSS severity bucket for coloring (hi ≥ 7, me ≥ 4, else lo).
const sevClass = (score) => {
  const n = Number(score)
  return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo'
}

// dd/mm/aaaa in the list; full local timestamp on hover.
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '—')
const fullDate = (iso) => (iso ? new Date(iso).toLocaleString('pt-BR') : '')

const opNames = (v) => {
  const ops = Array.isArray(v.operators) ? v.operators : []
  return ops.length ? ops.map((o) => o.username).join(', ') : '—'
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="hubPage" :class="{ withDetails: preview }">
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('hub.title') }}</h1>
        <p>{{ t('hub.subtitle') }}</p>
      </div>
    </div>

    <div class="hubTop">
      <div class="tabs">
        <button class="tab" :class="{ active: entity === 'vulns' }" @click="entity = 'vulns'">
          {{ t('hub.tabVulns') }}
        </button>
        <button class="tab" :class="{ active: entity === 'reports' }" @click="entity = 'reports'">
          {{ t('hub.tabReports') }}
        </button>
      </div>

      <!-- Filter bar occupies the space between the tabs and the Criar button.
           Future: each entity (vulns/reports) will carry its own filter state. -->
      <FilterBar ref="filterBar" class="hubFilter" v-model="query"
                 :dynamic-values="dynamicFilterValues" />

      <div class="toolbar">
        <span v-if="selected.size" class="selectionHint mono">
          {{ selected.size }} {{ t('hub.selected') }}
        </span>
        <button v-if="selected.size" class="btn">{{ t('hub.actions') }}</button>
        <button class="btn primary" @click="goCreate">
          {{ entity === 'vulns' ? t('hub.createVuln') : t('hub.createReport') }}
        </button>
      </div>
    </div>

    <!-- Reports tab: stub until the backend exists -->
    <section v-if="entity === 'reports'" class="panel stub">
      <p>{{ t('hub.tabReports') }} — {{ t('comingSoon') }}</p>
    </section>

    <template v-else>
      <div class="pagination top">
        <span class="pageInfo mono">{{ t('hub.showing') }} {{ rangeLabel }}</span>
        <button class="pageBtn" :disabled="page <= 1" @click="page--">{{ t('common.prev') }}</button>
        <button v-for="n in pageCount" :key="n" class="pageBtn"
                :class="{ active: n === page }" @click="page = n">{{ n }}</button>
        <button class="pageBtn" :disabled="page >= pageCount" @click="page++">{{ t('common.next') }}</button>
      </div>

      <section class="panel tablePanel" @scroll="menuFor = null">
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" class="check" :checked="allChecked"
                         :indeterminate.prop="someChecked" @change="toggleAll" /></th>
              <th>{{ t('cols.identifier') }}</th>
              <th>{{ t('cols.status') }}</th>
              <th>{{ t('cols.cvss') }}</th>
              <th>{{ t('cols.operators') }}</th>
              <th>{{ t('cols.source') }}</th>
              <th>{{ t('cols.createdAt') }}</th>
              <th>{{ t('cols.updatedAt') }}</th>
              <th style="text-align:center">{{ t('cols.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in pageRows" :key="v.id"
                :class="{ selected: selected.has(v.id), preview: preview?.id === v.id }">
              <td @click.stop><input type="checkbox" class="check"
                   :checked="selected.has(v.id)" @change="toggleRow(v.id)" /></td>
              <td class="val idcell" @click="openPreview(v)">{{ v.identifier || '—' }}</td>
              <td @click="openPreview(v)">
                <span class="pill" :class="'s-' + v.status">{{ t('status.' + v.status) }}</span>
              </td>
              <td @click="openPreview(v)">
                <span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ v.cvss_score }}</span>
                <span v-else>—</span>
              </td>
              <td class="val" @click="openPreview(v)">{{ opNames(v) }}</td>
              <td class="val" @click="openPreview(v)">{{ v.source || '—' }}</td>
              <td class="dateCell" :title="fullDate(v.created_at)" @click="openPreview(v)">{{ fmtDate(v.created_at) }}</td>
              <td class="dateCell" :title="fullDate(v.updated_at)" @click="openPreview(v)">{{ fmtDate(v.updated_at) }}</td>
              <td style="text-align:center" @click.stop>
                <div class="rowActionWrap">
                  <button class="link rowBtn" @click="toggleMenu(v.id, $event)">{{ t('common.rowMenu') }}</button>
                  <div v-if="menuFor === v.id" class="rowMenuInline" :style="menuPos">
                    <button @click="openPreview(v); menuFor = null">{{ t('rowActions.view') }}</button>
                    <button @click="goDetail(v.id)">{{ t('rowActions.detail') }}</button>
                    <button @click="goDetail(v.id)">{{ t('rowActions.edit') }}</button>
                    <button class="danger" @click="removeRow(v.id)">{{ t('rowActions.delete') }}</button>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && !pageRows.length">
              <td colspan="9" class="empty">{{ t('hub.empty') }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <p v-if="error" class="err">{{ error }}</p>
    </template>
    </div>

    <!-- Bottom details panel (§6/§7) -->
    <aside class="details" :class="{ open: preview }">
      <div v-if="preview" class="detailsInner">
        <div class="detailsTop">
          <span class="detailsId mono">{{ preview.internal_id || preview.identifier || t('vuln.draft') }}</span>
          <div class="detailsActions">
            <button class="btn" @click="goDetail(preview.id)">{{ t('rowActions.detail') }}</button>
            <button class="btn" @click="closePreview">{{ t('common.close') }}</button>
          </div>
        </div>
        <div class="detailCols">
          <div>
            <div class="kv"><label>{{ t('cols.status') }}</label>
              <span class="pill" :class="'s-' + preview.status">{{ t('status.' + preview.status) }}</span></div>
            <div class="kv"><label>{{ t('cols.cvss') }}</label>
              <span v-if="preview.cvss_score != null" class="cvss" :class="sevClass(preview.cvss_score)">{{ preview.cvss_score }}</span>
              <span v-else>—</span></div>
          </div>
          <div>
            <div class="kv"><label>{{ t('cols.identifier') }}</label>
              <span class="val">{{ preview.identifier || '—' }}</span></div>
            <div class="kv"><label>{{ t('cols.source') }}</label><span>{{ preview.source || '—' }}</span></div>
          </div>
        </div>
      </div>
    </aside>
  </AppShell>
</template>

<style scoped>
.hubTop { display: flex; align-items: center; margin-bottom: 18px; gap: 24px; border-bottom: 1px solid var(--line); }
.tabs { display: flex; gap: 24px; align-items: center; flex: 0 0 auto; }
.tab { border: 0; background: transparent; color: var(--muted); padding: 10px 0 9px; font-size: 14px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab:hover:not(.active) { color: var(--text); }
.tab.active { color: var(--text); border-color: var(--accent); }
.hubFilter { flex: 1 1 auto; min-width: 0; margin-bottom: 8px; }
.toolbar { display: flex; gap: 10px; align-items: center; flex: 0 0 auto; margin-bottom: 8px; }
.selectionHint { color: var(--muted); font-size: 12px; }
/* Only the list scrolls; title, tabs/filter and pagination stay put. While the
   details panel is open the page shrinks above it. */
.hubPage { height: 100%; display: flex; flex-direction: column; }
.hubPage.withDetails { padding-bottom: max(30vh, 220px); }
.hubPage > * { flex: 0 0 auto; }
.hubPage > .tablePanel { flex: 0 1 auto; min-height: 0; overflow: auto; }
.pagination.top { margin: 0 0 12px; }
thead th { position: sticky; top: 0; background: var(--panel); z-index: 1; box-shadow: inset 0 -1px 0 var(--line); }
th { border-bottom: 0; }
.stub { padding: 3rem; text-align: center; color: var(--muted); }

table { table-layout: fixed; }
th:nth-child(1), td:nth-child(1) { width: 48px; }
th:nth-child(2), td:nth-child(2) { width: 300px; }
th:nth-child(3), td:nth-child(3) { width: 150px; }
th:nth-child(4), td:nth-child(4) { width: 90px; }
th:nth-child(5), td:nth-child(5) { width: 220px; }
th:nth-child(6), td:nth-child(6) { width: 120px; }
th:nth-child(7), td:nth-child(7), th:nth-child(8), td:nth-child(8) { width: 120px; }
th:nth-child(9), td:nth-child(9) { width: 96px; }
.dateCell { color: var(--muted); font-variant-numeric: tabular-nums; }
th, td { white-space: nowrap; }
.val { overflow: hidden; text-overflow: ellipsis; }
td { cursor: pointer; }
tr.selected td, tr.preview td { background: var(--accent-soft); }

.rowActionWrap { position: relative; display: inline-flex; justify-content: center; }
.rowBtn { margin-left: 0; }
.rowMenuInline {
  position: fixed; min-width: 150px; border: 1px solid var(--line);
  display: flex; flex-direction: column;
  background: var(--panel); border-radius: var(--radius); box-shadow: var(--shadow-pop); padding: 4px; z-index: 50; text-align: left;
}
.rowMenuInline button { width: 100%; height: 30px; border: 0; background: transparent; color: var(--text-2); text-align: left; border-radius: var(--radius-sm); padding: 0 10px; font-size: 13px; }
.rowMenuInline button:hover { background: var(--hover); }
.rowMenuInline button.danger { color: var(--danger); }

.details {
  position: fixed; left: var(--sidebar); right: 0; bottom: 0; height: 30vh; min-height: 220px;
  background: var(--panel); border-top: 1px solid var(--line-2);
  z-index: 18; padding: 20px 32px;
  transform: translateY(100%); transition: transform .15s ease;
}
.details.open { transform: translateY(0); }
.detailsTop { display: flex; align-items: center; margin-bottom: 18px; }
.detailsId { font-size: 17px; color: var(--accent); }
.detailsActions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.detailCols { display: grid; grid-template-columns: 1fr 1fr; gap: 56px; max-width: 700px; }
.kv { margin-bottom: 16px; }
.kv label { display: block; color: var(--muted); margin-bottom: 6px; font-size: 12px; }
</style>
