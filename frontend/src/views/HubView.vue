<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  listVulns, deleteVuln, dispatchVuln, listReports, deleteReport, downloadAuthed, ApiError,
} from '../api'
import { useAuthStore } from '../stores/auth'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'
import FilterBar from '../components/FilterBar.vue'
import VulnTimeline from '../components/VulnTimeline.vue'
import { parseQuery } from '../filterQuery'
import { fmtDate, fmtDateTime, fmtPlainDate } from '../dates'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const isWriter = computed(() => ['admin', 'writer_all'].includes(auth.user?.role))

// Entity switcher (§5.4): vulnerabilities or reports.
// The tab lives in the URL (/hub?entity=reports) so reload and the back button keep it.
const fromQuery = (q) => (q === 'reports' ? 'reports' : 'vulns')
const entity = ref(fromQuery(route.query.entity))
watch(() => route.query.entity, (q) => { entity.value = fromQuery(q) })
watch(entity, (e) => {
  const wanted = e === 'reports' ? 'reports' : 'vulnerabilities'
  if (route.query.entity !== wanted) router.replace({ query: { ...route.query, entity: wanted } })
})

// Drive the global accent: reports -> indigo, vulns -> green. Sets a data
// attribute on <html> that [data-entity="reports"] in style.css keys off.
watch(entity, (e) => {
  document.documentElement.setAttribute('data-entity', e === 'reports' ? 'reports' : 'vulns')
}, { immediate: true })
onUnmounted(() => document.documentElement.removeAttribute('data-entity'))

const vulns = ref([])
const reports = ref([])
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
// Each tab starts clean: first page, nothing selected or previewed.
watch(entity, () => {
  page.value = 1
  preview.value = null
  menuFor.value = null
  selected.value = new Set()
})

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
  if (batchOpen.value && !e.target.closest('.batchWrap')) batchOpen.value = false
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

// Reports reuse the same filter grammar by exposing report fields under the
// names it understands: id/text -> "OP-0001 name client", source -> client, cvss -> max.
const filteredReports = computed(() => {
  let rows = reports.value.map((r) => ({
    ...r,
    identifier: [r.internal_id, r.name, r.client_name].filter(Boolean).join(' '),
    source: r.client_name,
    cvss_score: r.max_cvss,
  }))
  if (query.value.trim()) {
    const { predicate } = parseQuery(query.value)
    rows = rows.filter(predicate)
  }
  return rows
})
const activeRows = computed(() => (entity.value === 'vulns' ? filteredVulns.value : filteredReports.value))

// Distinct operator usernames across the loaded rows, for the operator: value menu.
const operatorValues = computed(() => {
  const set = new Set()
  for (const v of (entity.value === 'vulns' ? vulns.value : reports.value)) {
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
  try {
    const [v, r] = await Promise.all([listVulns(), listReports()])
    vulns.value = v
    reports.value = r
  }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

const total = computed(() => activeRows.value.length)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return activeRows.value.slice(start, start + pageSize.value)
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

// The drawer is as tall as its content; the list reserves exactly that space.
const detailsEl = ref(null)
const detailsH = ref(0)
let detailsObserver = null
onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !detailsEl.value) return
  detailsObserver = new ResizeObserver(() => { detailsH.value = detailsEl.value.offsetHeight })
  detailsObserver.observe(detailsEl.value)
})
onUnmounted(() => detailsObserver?.disconnect())

function openPreview(v) { preview.value = v; nextTick(() => { detailsH.value = detailsEl.value?.offsetHeight || 0 }) }
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

// --- Export / dispatch, one row or the whole selection ----------------------------
const notice = ref('')
const batchOpen = ref(false)
const batchPos = ref({})
const isVulns = computed(() => entity.value === 'vulns')
const selectedRows = computed(() => (isVulns.value ? vulns.value : reports.value).filter((r) => selected.value.has(r.id)))

function toggleBatch(ev) {
  batchOpen.value = !batchOpen.value
  if (!batchOpen.value) return
  const rect = ev.currentTarget.getBoundingClientRect()
  batchPos.value = { top: rect.bottom + 4 + 'px', right: window.innerWidth - rect.right + 'px' }
}

async function exportRows(ids, format) {
  error.value = ''; notice.value = ''
  try {
    if (isVulns.value) {
      await downloadAuthed('/vulnerabilities/export', 'vulnerabilidades', { method: 'POST', body: { ids, format } })
    } else {
      await downloadAuthed('/reports/export', 'relatorios', { method: 'POST', body: { ids } })
    }
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
}
const exportSelected = (format) => { batchOpen.value = false; return exportRows([...selected.value], format) }
// One row downloads the item itself (a PDF), not a ZIP of one.
async function exportRow(id, format) {
  menuFor.value = null
  error.value = ''; notice.value = ''
  const base = isVulns.value ? `/vulnerabilities/${id}` : `/reports/${id}`
  try { await downloadAuthed(`${base}/export?format=${format}`, isVulns.value ? 'vulnerabilidade.pdf' : 'relatorio.pdf') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
}

// "Disparar" applies to vulnerabilities saved locally; the rest are skipped, not failed.
const canDispatchRow = (v) => isWriter.value && v.status === 'saved_local'

async function dispatchRow(v) {
  menuFor.value = null
  if (!confirm(t('vuln.confirmDispatch'))) return
  error.value = ''; notice.value = ''
  try { await dispatchVuln(v.id); notice.value = t('vuln.dispatched'); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.dispatch') }
}

// Runs `fn` over the rows one by one and reports successes, skips and failures.
async function runBatch(rows, fn) {
  let done = 0
  const failures = []
  for (const r of rows) {
    try { await fn(r); done++ }
    catch (e) { failures.push(`${r.identifier || r.name || r.internal_id}: ${e instanceof ApiError ? e.detail : e.message}`) }
  }
  return { done, failures }
}
function reportBatch(label, { done, failures }, skipped = 0) {
  notice.value = t('hub.batchResult', { label, done, skipped, failed: failures.length })
  error.value = failures.slice(0, 3).join(' · ') + (failures.length > 3 ? ` (+${failures.length - 3})` : '')
}

async function dispatchSelected() {
  batchOpen.value = false
  const eligible = selectedRows.value.filter(canDispatchRow)
  if (!eligible.length) { error.value = t('hub.nothingToDispatch'); return }
  if (!confirm(t('hub.confirmBatchDispatch', { n: eligible.length }))) return
  error.value = ''; notice.value = ''
  const res = await runBatch(eligible, (v) => dispatchVuln(v.id))
  reportBatch(t('actions.dispatch'), res, selectedRows.value.length - eligible.length)
  selected.value = new Set(); await load()
}

async function deleteSelected() {
  batchOpen.value = false
  const rows = selectedRows.value
  if (!rows.length) return
  if (!confirm(t('hub.confirmBatchDelete', { n: rows.length }))) return
  error.value = ''; notice.value = ''
  const res = await runBatch(rows, (r) => (isVulns.value ? deleteVuln(r.id) : deleteReport(r.id)))
  reportBatch(t('rowActions.delete'), res)
  selected.value = new Set(); preview.value = null; await load()
}

function goDetail(id) { router.push(`/vulnerabilities/${id}`) }
function goReport(id) { router.push(`/reports/${id}`) }
function goCreate() { router.push(entity.value === 'vulns' ? '/vulnerabilities/new' : '/reports/new') }

async function removeRow(id) {
  menuFor.value = null
  const isVuln = entity.value === 'vulns'
  if (!confirm(t(isVuln ? 'vuln.confirmDelete' : 'reports.confirmDelete'))) return
  try {
    await (isVuln ? deleteVuln(id) : deleteReport(id))
    if (preview.value?.id === id) preview.value = null
    await load()
  }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

const period = (r) => (r.start_date || r.end_date)
  ? `${fmtPlainDate(r.start_date)} – ${fmtPlainDate(r.end_date)}` : '—'

// CVSS severity bucket for coloring (hi ≥ 7, me ≥ 4, else lo).
const sevClass = (score) => {
  const n = Number(score)
  return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo'
}

// dd/mm/aaaa in the list; full local timestamp on hover.
const fullDate = (iso) => (iso ? fmtDateTime(iso) : '')

const opNames = (v) => {
  const ops = Array.isArray(v.operators) ? v.operators : []
  return ops.length ? ops.map((o) => o.username).join(', ') : '—'
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="hubPage" :style="{ paddingBottom: preview ? detailsH + 'px' : '' }">
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
        <div v-if="selected.size" class="batchWrap">
          <button class="btn" @click="toggleBatch($event)">{{ t('hub.actions') }}</button>
          <div v-if="batchOpen" class="rowMenuInline" :style="batchPos">
            <button @click="exportSelected('pdf')">{{ t('hub.exportPdfZip') }}</button>
            <button v-if="isVulns" @click="exportSelected('xlsx')">{{ t('rpt.exportXlsx') }}</button>
            <button v-if="isVulns && isWriter" @click="dispatchSelected">{{ t('actions.dispatch') }}</button>
            <button v-if="isWriter" class="danger" @click="deleteSelected">{{ t('rowActions.delete') }}</button>
          </div>
        </div>
        <button v-if="isWriter" class="btn primary" @click="goCreate">
          {{ entity === 'vulns' ? t('hub.createVuln') : t('hub.createReport') }}
        </button>
      </div>
    </div>

      <p v-if="notice" class="ok msg">{{ notice }}</p>
      <p v-if="error" class="err msg">{{ error }}</p>

      <div class="pagination top">
        <span class="pageInfo mono">{{ t('hub.showing') }} {{ rangeLabel }}</span>
        <button class="pageBtn" :disabled="page <= 1" @click="page--">{{ t('common.prev') }}</button>
        <button v-for="n in pageCount" :key="n" class="pageBtn"
                :class="{ active: n === page }" @click="page = n">{{ n }}</button>
        <button class="pageBtn" :disabled="page >= pageCount" @click="page++">{{ t('common.next') }}</button>
      </div>

      <section v-if="entity === 'vulns'" class="panel tablePanel" @scroll="menuFor = null">
        <table class="vtable">
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
                    <button @click="exportRow(v.id, 'pdf')">{{ t('rowActions.export') }}</button>
                    <button v-if="canDispatchRow(v)" @click="dispatchRow(v)">{{ t('actions.dispatch') }}</button>
                    <button v-if="isWriter" class="danger" @click="removeRow(v.id)">{{ t('rowActions.delete') }}</button>
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

      <section v-else class="panel tablePanel" @scroll="menuFor = null">
        <table class="rtable">
          <thead>
            <tr>
              <th><input type="checkbox" class="check" :checked="allChecked"
                         :indeterminate.prop="someChecked" @change="toggleAll" /></th>
              <th>{{ t('rcols.name') }}</th>
              <th>{{ t('cols.status') }}</th>
              <th>{{ t('rcols.risk') }}</th>
              <th>{{ t('cols.operators') }}</th>
              <th>{{ t('rcols.client') }}</th>
              <th>{{ t('rcols.vulns') }}</th>
              <th>{{ t('cols.updatedAt') }}</th>
              <th style="text-align:center">{{ t('cols.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in pageRows" :key="r.id"
                :class="{ selected: selected.has(r.id), preview: preview?.id === r.id }">
              <td @click.stop><input type="checkbox" class="check"
                   :checked="selected.has(r.id)" @change="toggleRow(r.id)" /></td>
              <td class="val" @click="openPreview(r)">
                <span class="idcell">{{ r.internal_id }}</span> <span class="rname">{{ r.name }}</span>
              </td>
              <td @click="openPreview(r)">
                <span class="pill" :class="'s-' + r.status">{{ t('status.' + r.status) }}</span>
              </td>
              <td @click="openPreview(r)">
                <span v-if="r.max_cvss != null" class="cvss" :class="sevClass(r.max_cvss)">{{ r.max_cvss }}</span>
                <span v-else>—</span>
              </td>
              <td class="val" @click="openPreview(r)">{{ opNames(r) }}</td>
              <td class="val" @click="openPreview(r)">{{ r.client_name || '—' }}</td>
              <td class="dateCell" @click="openPreview(r)">{{ r.vuln_count }}</td>
              <td class="dateCell" :title="fullDate(r.updated_at)" @click="openPreview(r)">{{ fmtDate(r.updated_at) }}</td>
              <td style="text-align:center" @click.stop>
                <div class="rowActionWrap">
                  <button class="link rowBtn" @click="toggleMenu(r.id, $event)">{{ t('common.rowMenu') }}</button>
                  <div v-if="menuFor === r.id" class="rowMenuInline" :style="menuPos">
                    <button @click="openPreview(r); menuFor = null">{{ t('rowActions.view') }}</button>
                    <button @click="goReport(r.id)">{{ t('rowActions.open') }}</button>
                    <button @click="exportRow(r.id, 'pdf')">{{ t('rowActions.export') }}</button>
                    <button v-if="isWriter && r.status === 'draft'" class="danger" @click="removeRow(r.id)">{{ t('rowActions.delete') }}</button>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && !pageRows.length">
              <td colspan="9" class="empty">{{ t('hub.emptyReports') }}</td>
            </tr>
          </tbody>
        </table>
      </section>

    </div>

    <!-- Bottom details panel (§6/§7) -->
    <aside ref="detailsEl" class="details" :class="{ open: preview }">
      <div v-if="preview && entity === 'vulns'" class="detailsInner">
        <div class="detailsTop">
          <div class="headline">
            <span class="detailsId mono" :title="preview.identifier || ''">
              {{ preview.identifier || preview.internal_id || t('vuln.draft') }}
            </span>
          </div>
          <div class="detailsActions">
            <span class="pill statusPill" :class="'s-' + preview.status">{{ t('status.' + preview.status) }}</span>
            <span class="updated" :title="fullDate(preview.updated_at)">
              {{ t('cols.updatedAt') }} {{ fmtDateTime(preview.updated_at) }}
            </span>
            <button class="btn" @click="goDetail(preview.id)">{{ t('rowActions.detail') }}</button>
            <button class="btn" @click="closePreview">{{ t('common.close') }}</button>
          </div>
        </div>
        <h2 class="metaLine">
          <span class="m"><span class="k">{{ t('cols.cvss') }}</span>
            <span v-if="preview.cvss_score != null" class="cvss" :class="sevClass(preview.cvss_score)">{{ preview.cvss_score }}</span>
            <span v-else>—</span></span>
          <span class="m"><span class="k">{{ t('vform.cvssVector') }}</span>
            <span class="mono v">{{ preview.cvss_vector || '—' }}</span></span>
          <span class="m"><span class="k">{{ t('cols.source') }}</span>
            <span class="v">{{ preview.source || '—' }}</span></span>
          <span class="m"><span class="k">{{ t('hub.rvsShort') }}</span>
            <span class="mono v">{{ preview.rvs_id || '—' }}</span></span>
        </h2>
        <h2 class="opsLine">
          <template v-if="preview.operators?.length">
            <span v-for="o in preview.operators" :key="o.id" class="op">{{ o.username }}</span>
          </template>
          <span v-else class="none">—</span>
        </h2>
        <VulnTimeline :vuln="preview" compact class="drawerTimeline" />
      </div>

      <div v-else-if="preview" class="detailsInner">
        <div class="detailsTop">
          <div class="headline">
            <span class="detailsId" :title="preview.name">{{ preview.name }}</span>
          </div>
          <div class="detailsActions">
            <span class="pill statusPill" :class="'s-' + preview.status">{{ t('status.' + preview.status) }}</span>
            <span class="updated" :title="fullDate(preview.updated_at)">
              {{ t('cols.updatedAt') }} {{ fmtDateTime(preview.updated_at) }}
            </span>
            <button class="btn" @click="goReport(preview.id)">{{ t('rowActions.open') }}</button>
            <button class="btn" @click="closePreview">{{ t('common.close') }}</button>
          </div>
        </div>
        <h2 class="metaLine">
          <span class="m"><span class="k">ID</span><span class="mono v">{{ preview.internal_id }}</span></span>
          <span class="m"><span class="k">{{ t('rcols.client') }}</span><span class="v">{{ preview.client_name || '—' }}</span></span>
          <span class="m"><span class="k">{{ t('rcols.period') }}</span><span class="v">{{ period(preview) }}</span></span>
          <span class="m"><span class="k">{{ t('rcols.vulns') }}</span><span class="v">{{ preview.vuln_count }}</span></span>
          <span class="m"><span class="k">{{ t('rcols.risk') }}</span>
            <span v-if="preview.max_cvss != null" class="cvss" :class="sevClass(preview.max_cvss)">{{ preview.max_cvss }}</span>
            <span v-else>—</span></span>
        </h2>
        <h2 class="opsLine">
          <template v-if="preview.operators?.length">
            <span v-for="o in preview.operators" :key="o.id" class="op">{{ o.username }}</span>
          </template>
          <span v-else class="none">—</span>
        </h2>
        <p v-if="preview.lock" class="lockLine">
          {{ t('reports.editingBy', { user: preview.lock.holder_username }) }}
        </p>
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
.hubPage > * { flex: 0 0 auto; }
.hubPage > .tablePanel { flex: 0 1 auto; min-height: 0; overflow: auto; }
.pagination.top { margin: 0 0 12px; }
.msg { margin: 0 0 10px; font-size: 13px; }
.ok { color: var(--accent); }
.batchWrap { position: relative; }
thead th { position: sticky; top: 0; background: var(--panel); z-index: 1; box-shadow: inset 0 -1px 0 var(--line); }
th { border-bottom: 0; }
.stub { padding: 3rem; text-align: center; color: var(--muted); }

table { table-layout: fixed; }
.vtable th:nth-child(1), .vtable td:nth-child(1) { width: 48px; }
/* Column 2 (identifier) has no width: it takes whatever the fixed columns leave. */
.vtable th:nth-child(3), .vtable td:nth-child(3) { width: 150px; }
.vtable th:nth-child(4), .vtable td:nth-child(4) { width: 90px; }
.vtable th:nth-child(5), .vtable td:nth-child(5) { width: 180px; }
.vtable th:nth-child(6), .vtable td:nth-child(6) { width: 120px; }
.vtable th:nth-child(7), .vtable td:nth-child(7), .vtable th:nth-child(8), .vtable td:nth-child(8) { width: 110px; }
.vtable th:nth-child(9), .vtable td:nth-child(9) { width: 96px; }
.rtable th:nth-child(1), .rtable td:nth-child(1) { width: 48px; }
/* Column 2 (report name) is the flexible one. */
.rtable th:nth-child(3), .rtable td:nth-child(3) { width: 140px; }
.rtable th:nth-child(4), .rtable td:nth-child(4) { width: 90px; }
.rtable th:nth-child(5), .rtable td:nth-child(5) { width: 180px; }
.rtable th:nth-child(6), .rtable td:nth-child(6) { width: 160px; }
.rtable th:nth-child(7), .rtable td:nth-child(7) { width: 90px; }
.rtable th:nth-child(8), .rtable td:nth-child(8) { width: 120px; }
.rtable th:nth-child(9), .rtable td:nth-child(9) { width: 96px; }
.rname { color: var(--text); }
.lockLine { margin: 4px 0 0; font-size: 12px; color: var(--st-wait-fg); }
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
  position: fixed; left: var(--sidebar); right: 0; bottom: 0;
  background: var(--panel); border-top: 1px solid var(--line-2);
  z-index: 18; padding: 14px 32px 14px; max-height: 60vh; overflow: auto;
  transform: translateY(100%); transition: transform .15s ease;
}
.details.open { transform: translateY(0); }
.detailsTop { display: flex; align-items: center; gap: 16px; margin-bottom: 10px; }
.headline { display: flex; align-items: center; gap: 14px; min-width: 0; flex: 1 1 auto; }
.detailsId { font-size: 17px; color: var(--accent); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.statusPill { flex: 0 0 auto; margin-right: 6px; }
.updated { flex: 0 0 auto; margin-right: 6px; font-size: 12px; color: var(--dim); }
.detailsActions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.metaLine, .opsLine { margin: 0 0 8px; font-size: 13px; font-weight: 300; color: var(--text-2); }
.metaLine { display: flex; flex-wrap: wrap; gap: 2px 28px; }
.metaLine .k { margin-right: 8px; font-size: 12px; color: var(--muted); }
.metaLine .v { word-break: break-all; }
.opsLine { display: flex; flex-wrap: wrap; gap: 6px; }
.op { padding: 1px 9px; border: 1px solid var(--line-2); border-radius: var(--radius); font-size: 12px; color: var(--text-2); }
.none { color: var(--dim); }
.drawerTimeline { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); }
</style>
