<script setup>
// The defense team's list (D17), laid out like the Hub: work tabs, the filter bar,
// pagination, and a batch menu to accept or assume the risk of many vulns at once.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { defenseVulns, defenseAccept, defenseAcceptRisk, ApiError } from '../api'
import { t } from '../i18n'
import { fmtDate, fmtDateTime } from '../dates'
import { confirmDialog, promptDialog } from '../dialog'
import { DEFENSE_FILTER_KEYS, parseQuery } from '../filterQuery'
import AppShell from '../components/AppShell.vue'
import FilterBar from '../components/FilterBar.vue'

const router = useRouter()
const items = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const isNew = (v) => v.status === 'sent' && !v.accepted_at
const TABS = [
  { key: 'new', test: isNew },
  { key: 'awaitingRvs', test: (v) => v.status === 'sent' && !!v.accepted_at },
  { key: 'inProgress', test: (v) => ['fixing', 'retesting'].includes(v.status) },
  { key: 'fixed', test: (v) => v.status === 'fixed' },
  { key: 'riskAccepted', test: (v) => v.status === 'risk_accepted' },
  { key: 'all', test: () => true },
]
// Tabs where a report name selects that report's vulns, to act on them together.
const REPORT_PICK_TABS = ['new', 'awaitingRvs', 'riskAccepted']
const tab = ref('new')
const count = (key) => items.value.filter(TABS.find((x) => x.key === key).test).length

// The filter applies within the tab (the report field is matched by name, as in the Hub).
const query = ref('')
const filterBar = ref(null)
const rows = computed(() => {
  let list = items.value.filter(TABS.find((x) => x.key === tab.value).test)
  if (query.value.trim()) list = list.filter(parseQuery(query.value).predicate)
  return list
})

// Pagination, as in the Hub (fixed page size).
const pageSize = 50
const page = ref(1)
const pageCount = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize)))
const pageRows = computed(() => rows.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const rangeLabel = computed(() => {
  const total = rows.value.length
  if (!total) return `0 ${t('hub.of')} 0`
  const start = (page.value - 1) * pageSize + 1
  return `${start}-${Math.min(page.value * pageSize, total)} ${t('hub.of')} ${total}`
})

// Selection: a new tab or filter starts clean.
const selected = ref(new Set())
watch([tab, query], () => { page.value = 1; selected.value = new Set() })
const allChecked = computed(() => pageRows.value.length > 0 && pageRows.value.every((v) => selected.value.has(v.id)))
const someChecked = computed(() => pageRows.value.some((v) => selected.value.has(v.id)) && !allChecked.value)
function toggleAll(e) {
  for (const v of pageRows.value) e.target.checked ? selected.value.add(v.id) : selected.value.delete(v.id)
  selected.value = new Set(selected.value)
}
function toggleRow(id) {
  selected.value.has(id) ? selected.value.delete(id) : selected.value.add(id)
  selected.value = new Set(selected.value)
}
const selectedRows = computed(() => items.value.filter((v) => selected.value.has(v.id)))

// Selects every vuln of the report in this tab (all pages, within the filter);
// a second click, with all of them selected, clears them.
const reportPick = computed(() => REPORT_PICK_TABS.includes(tab.value))
function pickReport(report) {
  const ids = rows.value.filter((v) => v.report?.id === report.id).map((v) => v.id)
  const all = ids.every((id) => selected.value.has(id))
  for (const id of ids) all ? selected.value.delete(id) : selected.value.add(id)
  selected.value = new Set(selected.value)
}

const sevClass = (s) => { const n = Number(s); return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo' }
// Where the vuln stands for the defense team; "sent" is split by acceptance.
const stateLabel = (v) => (v.status === 'sent' ? t(v.accepted_at ? 'defense.awaitingRvs' : 'defense.new') : t('status.' + v.status))
const stateClass = (v) => (isNew(v) ? 's-ready' : 's-' + v.status)

async function load() {
  loading.value = true; error.value = ''
  try { items.value = await defenseVulns() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

// --- Batch actions ---------------------------------------------------------------
const batchOpen = ref(false)
const batchPos = ref({})
function toggleBatch(ev) {
  batchOpen.value = !batchOpen.value
  if (!batchOpen.value) return
  const rect = ev.currentTarget.getBoundingClientRect()
  batchPos.value = { top: rect.bottom + 4 + 'px', right: window.innerWidth - rect.right + 'px' }
}
function onDocClick(e) { if (batchOpen.value && !e.target.closest('.batchWrap')) batchOpen.value = false }
function onKeydown(e) {
  const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)
  if (e.key === '/' && !typing) { e.preventDefault(); filterBar.value?.focusAndTrigger() }
}

// One by one, reporting successes, skips and failures (as the Hub does).
async function runBatch(list, fn, label) {
  let done = 0
  const failures = []
  for (const v of list) {
    try { await fn(v); done++ }
    catch (e) { failures.push(`${v.identifier || v.internal_id}: ${e instanceof ApiError ? e.detail : e.message}`) }
  }
  notice.value = t('hub.batchResult', { label, done, skipped: selectedRows.value.length - list.length, failed: failures.length })
  error.value = failures.slice(0, 3).join(' · ') + (failures.length > 3 ? ` (+${failures.length - 3})` : '')
  selected.value = new Set()
  await load()
}

async function acceptSelected() {
  batchOpen.value = false
  error.value = ''; notice.value = ''
  const list = selectedRows.value.filter(isNew)
  if (!list.length) { error.value = t('defense.nothingToAccept'); return }
  if (!(await confirmDialog(t('defense.confirmBatchAccept', { n: list.length })))) return
  await runBatch(list, (v) => defenseAccept(v.id), t('defense.accept'))
}

async function acceptRiskSelected() {
  batchOpen.value = false
  error.value = ''; notice.value = ''
  const list = selectedRows.value.filter((v) => v.status === 'sent')
  if (!list.length) { error.value = t('defense.nothingToRisk'); return }
  const reason = await promptDialog(t('defense.riskPromptBatch', { n: list.length }), { ok: t('defense.acceptRisk') })
  if (reason === null) return
  if (reason.trim().length < 5) { error.value = t('defense.riskShort'); return }
  await runBatch(list, (v) => defenseAcceptRisk(v.id, reason.trim()), t('defense.acceptRisk'))
}

onMounted(() => {
  document.documentElement.setAttribute('data-entity', 'vulns')
  document.addEventListener('click', onDocClick)
  window.addEventListener('keydown', onKeydown)
  load()
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="top">
        <div class="tabs">
          <button v-for="x in TABS" :key="x.key" class="tab" :class="{ active: tab === x.key }" @click="tab = x.key">
            {{ t('defense.tabs.' + x.key) }} <span class="n">{{ count(x.key) }}</span>
          </button>
        </div>
        <FilterBar ref="filterBar" v-model="query" class="filter" :keys="DEFENSE_FILTER_KEYS" help="filter.defenseHelp" />
        <div class="toolbar">
          <span v-if="selected.size" class="selectionHint mono">{{ selected.size }} {{ t('hub.selected') }}</span>
          <div v-if="selected.size" class="batchWrap">
            <button class="btn" @click="toggleBatch($event)">{{ t('hub.actions') }}</button>
            <div v-if="batchOpen" class="rowMenuInline" :style="batchPos">
              <button @click="acceptSelected">{{ t('defense.accept') }}</button>
              <button @click="acceptRiskSelected">{{ t('defense.acceptRisk') }}</button>
            </div>
          </div>
        </div>
      </div>

      <p v-if="notice" class="ok msg">{{ notice }}</p>
      <p v-if="error" class="err msg">{{ error }}</p>

      <div class="pagination top">
        <span class="pageInfo mono">{{ t('hub.showing') }} {{ rangeLabel }}</span>
        <button class="pageBtn" :disabled="page <= 1" @click="page--">{{ t('common.prev') }}</button>
        <button v-for="n in pageCount" :key="n" class="pageBtn" :class="{ active: n === page }" @click="page = n">{{ n }}</button>
        <button class="pageBtn" :disabled="page >= pageCount" @click="page++">{{ t('common.next') }}</button>
      </div>

      <section class="panel tablePanel">
        <table class="dtable">
          <thead>
            <tr>
              <th><input type="checkbox" class="check" :checked="allChecked" :indeterminate.prop="someChecked" @change="toggleAll" /></th>
              <th>{{ t('cols.identifier') }}</th>
              <th>{{ t('defense.state') }}</th>
              <th>{{ t('cols.cvss') }}</th>
              <th>{{ t('defense.report') }}</th>
              <th>{{ t('defense.receivedAt') }}</th>
              <th>{{ t('rvs.rvsId') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in pageRows" :key="v.id" :class="{ selected: selected.has(v.id) }"
                @click="router.push(`/defense/vulnerabilities/${v.id}`)">
              <td @click.stop><input type="checkbox" class="check" :checked="selected.has(v.id)" @change="toggleRow(v.id)" /></td>
              <td class="val idcell" :title="v.identifier">{{ v.identifier || '—' }}</td>
              <td><span class="pill" :class="stateClass(v)">{{ stateLabel(v) }}</span></td>
              <td>
                <span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ Number(v.cvss_score).toFixed(1) }}</span>
                <span v-else>—</span>
              </td>
              <td class="val muted" :title="v.report?.name">
                <a v-if="v.report && reportPick" class="repLink" @click.stop="pickReport(v.report)">{{ v.report.name }}</a>
                <template v-else>{{ v.report?.name || '—' }}</template>
              </td>
              <td class="dateCell" :title="fmtDateTime(v.sent_at)">{{ fmtDate(v.sent_at) }}</td>
              <td class="val mono">{{ v.rvs_id || '—' }}</td>
            </tr>
            <tr v-if="!loading && !pageRows.length"><td colspan="7" class="empty">{{ t('defense.empty') }}</td></tr>
          </tbody>
        </table>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
/* The Hub's layout: only the list scrolls. */
.page { height: 100%; display: flex; flex-direction: column; }
.page > * { flex: 0 0 auto; }
.page > .tablePanel { flex: 0 1 auto; min-height: 0; overflow: auto; }
.top { display: flex; align-items: center; gap: 24px; margin-bottom: 18px; border-bottom: 1px solid var(--line); }
.tabs { display: flex; gap: 24px; flex: 0 0 auto; }
.tab { border: 0; background: transparent; color: var(--muted); padding: 10px 0 9px; font-size: 14px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab:hover:not(.active) { color: var(--text); }
.tab.active { color: var(--text); border-color: var(--accent); }
.tab .n { margin-left: 4px; font-size: 12px; color: var(--dim); }
.filter { flex: 1 1 auto; min-width: 0; margin-bottom: 8px; }
.toolbar { display: flex; gap: 10px; align-items: center; flex: 0 0 auto; margin-bottom: 8px; }
.selectionHint { color: var(--muted); font-size: 12px; }
.batchWrap { position: relative; }
.pagination.top { margin: 0 0 12px; }
.msg { margin: 0 0 10px; font-size: 13px; }
.ok { color: var(--accent); }

thead th { position: sticky; top: 0; background: var(--panel); z-index: 1; box-shadow: inset 0 -1px 0 var(--line); }
th { border-bottom: 0; }
table { table-layout: fixed; }
th, td { white-space: nowrap; }
td { cursor: pointer; }
.val { overflow: hidden; text-overflow: ellipsis; }
.dtable th:nth-child(1), .dtable td:nth-child(1) { width: 48px; }
.dtable th:nth-child(3), .dtable td:nth-child(3) { width: 150px; }
.dtable th:nth-child(4), .dtable td:nth-child(4) { width: 80px; }
.dtable th:nth-child(5), .dtable td:nth-child(5) { width: 26%; }
.dtable th:nth-child(6), .dtable td:nth-child(6) { width: 120px; }
.dtable th:nth-child(7), .dtable td:nth-child(7) { width: 160px; }
.dateCell { color: var(--muted); font-variant-numeric: tabular-nums; }
.mono { font-family: var(--mono); font-size: 12px; }
tr.selected td { background: var(--accent-soft); }
.repLink { color: var(--report-ink); cursor: pointer; }
.repLink:hover { text-decoration: underline; }

.rowMenuInline {
  position: fixed; min-width: 160px; border: 1px solid var(--line); display: flex; flex-direction: column;
  background: var(--panel); border-radius: var(--radius); box-shadow: var(--shadow-pop); padding: 4px; z-index: 50;
}
.rowMenuInline button { width: 100%; height: 30px; border: 0; background: transparent; color: var(--text-2); text-align: left; border-radius: var(--radius-sm); padding: 0 10px; font-size: 13px; }
.rowMenuInline button:hover { background: var(--hover); }
</style>
