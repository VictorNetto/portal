<script setup>
// One section of the defense team's work (D17), laid out like the Hub: the filter bar,
// pagination, and a batch menu with the actions that fit the section's vulns.
// Each section is its own page in the left rail (defenseSections.js).
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { defenseVulns, defenseAccept, defenseAcceptRisk, defenseSetRvs, defenseUndoRisk, ApiError } from '../api'
import { t } from '../i18n'
import { fmtDate, fmtDateTime } from '../dates'
import { confirmDialog, promptDialog } from '../dialog'
import { DEFENSE_FILTER_KEYS, parseQuery } from '../filterQuery'
import AppShell from '../components/AppShell.vue'
import FilterBar from '../components/FilterBar.vue'
import { SECTIONS } from '../defenseSections'

const router = useRouter()
const route = useRoute()
const items = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const byKey = Object.fromEntries(SECTIONS.map((s) => [s.key, s]))
const isNew = byKey.new.test
const awaitingRvs = byKey.awaitingRvs.test
const riskAccepted = byKey.riskAccepted.test
// Each section offers only what its vulns allow. Fixing, retesting and fixed belong to the
// red team now, so those sections have no actions (and no selection).
const SECTION_ACTIONS = {
  new: ['accept', 'acceptRisk'],
  awaitingRvs: ['rvs', 'acceptRisk'],
  inProgress: [],
  fixed: [],
  riskAccepted: ['undoRisk'],
}
const tab = computed(() => route.meta.section || 'new')
const section = computed(() => byKey[tab.value])
const tabActions = computed(() => SECTION_ACTIONS[tab.value])
// Selecting (checkboxes, and report names that select their vulns) only where something can follow.
const selectable = computed(() => tabActions.value.length > 0)

// The filter applies within the tab (the report field is matched by name, as in the Hub).
const query = ref('')
const filterBar = ref(null)
const rows = computed(() => {
  let list = items.value.filter(section.value.test)
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

// Each section starts clean; a new filter starts on page 1 with nothing selected.
const selected = ref(new Set())
watch(tab, () => { query.value = ''; notice.value = ''; error.value = '' })
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

// `fits`: which vulns the action applies to. `ask`: what to confirm or ask first; it resolves
// to the value the action needs (true for a plain confirmation), or false/null to stop.
// `invalid`: an error message key when the value typed can't be used.
const ACTIONS = {
  accept: {
    label: 'defense.accept', fits: isNew,
    ask: (n) => confirmDialog(t('defense.confirmBatchAccept', { n })),
    run: (v) => defenseAccept(v.id),
  },
  // Each vuln gets its own RVS ID, so this one opens a form instead of a single question.
  rvs: { label: 'rvs.enter', fits: awaitingRvs, form: true },
  acceptRisk: {
    label: 'defense.acceptRisk', fits: (v) => v.status === 'sent',
    ask: (n) => promptDialog(t('defense.riskPromptBatch', { n }), { ok: t('defense.acceptRisk') }),
    invalid: (reason) => (reason.trim().length >= 5 ? '' : 'defense.riskShort'),
    run: (v, reason) => defenseAcceptRisk(v.id, reason.trim()),
  },
  undoRisk: {
    label: 'defense.undoRisk', fits: riskAccepted,
    ask: (n) => confirmDialog(t('defense.confirmBatchUndoRisk', { n })),
    run: (v) => defenseUndoRisk(v.id),
  },
}

async function runAction(key) {
  const action = ACTIONS[key]
  batchOpen.value = false
  error.value = ''; notice.value = ''
  const list = selectedRows.value.filter(action.fits)
  if (!list.length) { error.value = t('defense.nothingFor', { action: t(action.label) }); return }
  if (action.form) { openRvsForm(list); return }
  const value = await action.ask(list.length)
  if (value === null || value === false) return
  const invalid = action.invalid?.(value)
  if (invalid) { error.value = t(invalid); return }
  await runBatch(list, (v) => action.run(v, value), t(action.label))
}

// --- Batch RVS: one field per vuln --------------------------------------------------
// A blank field is left for later. Each ID may be used once (the server checks against every
// vuln; the form catches repeats within itself first). Recorded rows leave the form; rows that
// failed stay with their reason.
const rvsForm = ref(null)  // { rows: [{ v, value, error }], busy }
function openRvsForm(list) {
  rvsForm.value = { rows: list.map((v) => ({ v, value: '', error: '' })), busy: false }
}
const rvsKey = (s) => s.trim().toLowerCase()
async function submitRvsForm() {
  const form = rvsForm.value
  const filled = form.rows.filter((r) => r.value.trim())
  if (!filled.length) return
  const seen = new Map()
  for (const r of form.rows) r.error = ''
  for (const r of filled) {
    const k = rvsKey(r.value)
    if (seen.has(k)) { r.error = seen.get(k).error = t('defense.rvsRepeated') } else seen.set(k, r)
  }
  if (filled.some((r) => r.error)) return
  form.busy = true
  let done = 0
  for (const r of filled) {
    try { await defenseSetRvs(r.v.id, r.value.trim()); done++; r.done = true }
    catch (e) { r.error = e instanceof ApiError ? e.detail : t('errors.register') }
  }
  form.rows = form.rows.filter((r) => !r.done)
  form.busy = false
  notice.value = t('defense.rvsFormResult', { done })
  selected.value = new Set()
  await load()
  if (!form.rows.some((r) => r.error)) rvsForm.value = null
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
      <div class="pageTop">
        <div class="titleBlock">
          <h1>{{ t('defense.tabs.' + tab) }}</h1>
          <p>{{ t('defense.hints.' + tab) }}</p>
        </div>
      </div>
      <div class="top">
        <FilterBar ref="filterBar" v-model="query" class="filter" :keys="DEFENSE_FILTER_KEYS" help="filter.defenseHelp" />
        <div class="toolbar">
          <span v-if="selected.size" class="selectionHint mono">{{ selected.size }} {{ t('hub.selected') }}</span>
          <div v-if="selected.size" class="batchWrap">
            <button class="btn" @click="toggleBatch($event)">{{ t('hub.actions') }}</button>
            <div v-if="batchOpen" class="rowMenuInline" :style="batchPos">
              <button v-for="a in tabActions" :key="a" @click="runAction(a)">{{ t(ACTIONS[a].label) }}</button>
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
              <th><input v-if="selectable" type="checkbox" class="check" :checked="allChecked" :indeterminate.prop="someChecked" @change="toggleAll" /></th>
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
                @click="router.push({ path: `/defense/vulnerabilities/${v.id}`, query: { from: tab } })">
              <td @click.stop><input v-if="selectable" type="checkbox" class="check" :checked="selected.has(v.id)" @change="toggleRow(v.id)" /></td>
              <td class="val idcell" :title="v.identifier">{{ v.identifier || '—' }}</td>
              <td><span class="pill" :class="stateClass(v)">{{ stateLabel(v) }}</span></td>
              <td>
                <span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ Number(v.cvss_score).toFixed(1) }}</span>
                <span v-else>—</span>
              </td>
              <td class="val muted" :title="v.report?.name">
                <a v-if="v.report && selectable" class="repLink" @click.stop="pickReport(v.report)">{{ v.report.name }}</a>
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

    <div v-if="rvsForm" class="modalBack" @click.self="rvsForm = null" @keydown.esc="rvsForm = null">
      <form class="panel modal rvsModal" role="dialog" aria-modal="true" :aria-label="t('rvs.enter')"
            @submit.prevent="submitRvsForm">
        <h2 class="secTitle">{{ t('rvs.enter') }}</h2>
        <p class="hint">{{ t('defense.rvsFormHint') }}</p>
        <div class="rvsRows">
          <label v-for="(r, i) in rvsForm.rows" :key="r.v.id" class="rvsRow">
            <span class="who" :title="r.v.identifier">
              <span class="mono">{{ r.v.internal_id }}</span>{{ r.v.identifier || '—' }}
            </span>
            <input v-model="r.value" :placeholder="t('rvs.placeholder')" maxlength="200" :class="{ invalid: r.error }"
                   :autofocus="i === 0" />
            <small v-if="r.error" class="fieldErr">{{ r.error }}</small>
          </label>
        </div>
        <div class="modalActions">
          <button type="button" class="btn" @click="rvsForm = null">{{ t('dialog.cancel') }}</button>
          <button class="btn primary" :disabled="rvsForm.busy || !rvsForm.rows.some((r) => r.value.trim())">
            {{ t('rvs.enter') }}
          </button>
        </div>
      </form>
    </div>
  </AppShell>
</template>

<style scoped>
/* The Hub's layout: only the list scrolls. */
.page { height: 100%; display: flex; flex-direction: column; }
.page > * { flex: 0 0 auto; }
.page > .tablePanel { flex: 0 1 auto; min-height: 0; overflow: auto; }
.top { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.filter { flex: 1 1 auto; min-width: 0; }
.toolbar { display: flex; gap: 10px; align-items: center; flex: 0 0 auto; }
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

.rvsModal { width: min(720px, 100%); }
.rvsRows { display: grid; gap: 10px; max-height: 55vh; overflow: auto; padding-right: 4px; }
.rvsRow { display: grid; grid-template-columns: minmax(0, 1fr) 220px; gap: 4px 12px; align-items: center; }
.rvsRow .who { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text); }
.rvsRow .who .mono { margin-right: 8px; color: var(--accent); }
.rvsRow input { font-family: var(--mono); font-size: 13px; }
.rvsRow input.invalid { border-color: var(--danger); }
.rvsRow .fieldErr { grid-column: 2; color: var(--danger); font-size: 12px; }
</style>
