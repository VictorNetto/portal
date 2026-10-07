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
const pageSize = ref(5)
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
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

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
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao carregar' }
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
function toggleMenu(id) { menuFor.value = menuFor.value === id ? null : id }

function goDetail(id) { router.push(`/vulnerabilities/${id}`) }
function goCreate() { router.push('/vulnerabilities/new') }

async function removeRow(id) {
  menuFor.value = null
  if (!confirm('Excluir esta vulnerabilidade?')) return
  try { await deleteVuln(id); if (preview.value?.id === id) preview.value = null; await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao excluir' }
}

// CVSS severity bucket for coloring (hi ≥ 7, me ≥ 4, else lo).
const sevClass = (score) => {
  const n = Number(score)
  return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo'
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1 class="mono">{{ t('hub.title') }}</h1>
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
        <button v-if="selected.size" class="btn">ϟ {{ t('hub.actions') }}</button>
        <button class="btn primary create" @click="goCreate">
          ＋ {{ entity === 'vulns' ? t('hub.createVuln') : t('hub.createReport') }}
        </button>
      </div>
    </div>

    <!-- Reports tab: stub until the backend exists -->
    <section v-if="entity === 'reports'" class="panel stub">
      <p>📋 {{ t('hub.tabReports') }} — {{ t('comingSoon') }}</p>
    </section>

    <template v-else>
      <section class="panel tablePanel">
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
                <span class="pill" :class="'s-' + v.status">{{ v.status }}</span>
              </td>
              <td @click="openPreview(v)">
                <span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ v.cvss_score }}</span>
                <span v-else>—</span>
              </td>
              <td class="val" @click="openPreview(v)">—</td>
              <td class="val" @click="openPreview(v)">{{ v.source || '—' }}</td>
              <td style="text-align:center" @click.stop>
                <div class="rowActionWrap">
                  <button class="kebab" @click="toggleMenu(v.id)">⋮</button>
                  <div v-if="menuFor === v.id" class="rowMenuInline">
                    <button @click="openPreview(v); menuFor = null">◉ {{ t('rowActions.view') }}</button>
                    <button @click="goDetail(v.id)">▤ {{ t('rowActions.detail') }}</button>
                    <button @click="goDetail(v.id)">✎ {{ t('rowActions.edit') }}</button>
                    <button class="danger" @click="removeRow(v.id)">⌫ {{ t('rowActions.delete') }}</button>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && !pageRows.length">
              <td colspan="7" class="empty">{{ t('hub.empty') }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <p v-if="error" class="err">{{ error }}</p>

      <div class="pagination">
        <span class="pageInfo mono">{{ t('hub.showing') }} {{ rangeLabel }}</span>
        <label class="muted">{{ t('hub.rows') }}</label>
        <select class="pageSelect" v-model.number="pageSize" @change="page = 1">
          <option>5</option><option>10</option><option>15</option>
        </select>
        <button class="pageBtn" :disabled="page <= 1" @click="page--">‹</button>
        <button v-for="n in pageCount" :key="n" class="pageBtn"
                :class="{ active: n === page }" @click="page = n">{{ n }}</button>
        <button class="pageBtn" :disabled="page >= pageCount" @click="page++">›</button>
      </div>
    </template>

    <!-- Bottom details panel (§6/§7) -->
    <aside class="details" :class="{ open: preview }">
      <div v-if="preview" class="detailsInner">
        <div class="detailsTop">
          <span class="detailsId mono">{{ preview.internal_id || preview.identifier || 'Rascunho' }}</span>
          <div class="detailsActions">
            <button class="btn" @click="goDetail(preview.id)">▤ {{ t('rowActions.detail') }}</button>
            <button class="xbtn" @click="closePreview">×</button>
          </div>
        </div>
        <div class="detailCols">
          <div>
            <div class="kv"><label>{{ t('cols.status') }}</label>
              <span class="pill" :class="'s-' + preview.status">{{ preview.status }}</span></div>
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
.pageTop { display: flex; align-items: flex-start; gap: 20px; margin-bottom: 18px; }
.titleBlock h1 { margin: 0 0 4px; font-weight: 650; font-size: 24px; color: var(--text); letter-spacing: -.01em; }
.titleBlock p { margin: 0; color: var(--muted); font-size: 13px; }

.hubTop { display: flex; align-items: center; margin-bottom: 16px; gap: 24px; }
.tabs { display: flex; gap: 24px; align-items: center; flex: 0 0 auto; }
.tab { border: 0; background: transparent; color: var(--muted); padding: 10px 0 9px; font-size: 14px; font-weight: 500; border-bottom: 2px solid transparent; }
.tab.active { color: var(--accent); border-color: var(--accent); }

.hubFilter { flex: 1 1 auto; min-width: 0; }
.toolbar { display: flex; gap: 12px; align-items: center; flex: 0 0 auto; }
.selectionHint { color: var(--muted); font-size: 12px; align-self: center; }

.btn {
  border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); height: 36px;
  padding: 0 14px; color: var(--text-2); display: inline-flex; align-items: center; gap: 8px; font-weight: 500;
}
.btn:hover { border-color: var(--dim); background: var(--hover); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-contrast); font-weight: 600; box-shadow: var(--shadow); }
.btn.primary:hover { background: var(--accent); filter: brightness(1.05); }
.create { width: 200px; justify-content: center; white-space: nowrap; }

.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); }
.stub { padding: 3rem; text-align: center; color: var(--muted); }
.tablePanel { overflow: hidden; }

table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th:nth-child(1), td:nth-child(1) { width: 48px; }
th:nth-child(2), td:nth-child(2) { width: 220px; }
th:nth-child(3), td:nth-child(3) { width: 150px; }
th:nth-child(4), td:nth-child(4) { width: 90px; }
th:nth-child(5), td:nth-child(5) { width: 220px; }
th:nth-child(6), td:nth-child(6) { width: 160px; }
th:nth-child(7), td:nth-child(7) { width: 82px; }
.val { overflow: hidden; text-overflow: ellipsis; }
th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 12px 16px; white-space: nowrap; }
th { color: #7a8698; font-weight: 600; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; background: var(--panel-2); }
td { color: var(--text-2); cursor: pointer; font-size: 13px; }
tbody tr:last-child td { border-bottom: 0; }
.idcell { font-family: var(--mono); color: var(--accent); font-weight: 500; }
tr:hover td { background: var(--hover); }
tr.selected td { background: var(--accent-soft); }
tr.preview td { background: var(--accent-soft); box-shadow: inset 3px 0 0 var(--accent); }
.check { width: 16px; height: 16px; accent-color: var(--accent); }
.empty { text-align: center; color: var(--muted); cursor: default; padding: 2.5rem; }

/* Status pills — semantic light colors keyed by status class */
.pill { display: inline-flex; align-items: center; border-radius: 999px; padding: 3px 9px; font-size: 11px; font-weight: 600; }
.pill.s-draft { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.pill.s-saved_local { color: var(--st-local-fg); background: var(--st-local-bg); }
.pill.s-dispatching, .pill.s-waiting_fix { color: var(--st-wait-fg); background: var(--st-wait-bg); }
.pill.s-dispatched { color: var(--st-dispatch-fg); background: var(--st-dispatch-bg); }
.pill.s-acknowledged { color: var(--st-ack-fg); background: var(--st-ack-bg); }
.pill.s-pending_retest { color: var(--st-retest-fg); background: var(--st-retest-bg); }
.pill.s-fixed { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }

.cvss { font-family: var(--mono); font-weight: 700; }
.cvss.hi { color: var(--sev-hi); } .cvss.me { color: var(--sev-me); } .cvss.lo { color: var(--sev-lo); }

.rowActionWrap { position: relative; display: inline-flex; justify-content: center; }
.kebab { border: 0; background: transparent; font-size: 20px; color: var(--muted); padding: 2px 8px; }
.kebab:hover { color: var(--text); }
.rowMenuInline {
  position: absolute; right: 0; top: 30px; min-width: 168px; border: 1px solid var(--line);
  background: var(--panel); border-radius: var(--radius-sm); box-shadow: var(--shadow-pop); padding: 6px; z-index: 50; text-align: left;
}
.rowMenuInline button { width: 100%; height: 34px; border: 0; background: transparent; color: var(--text-2); display: flex; align-items: center; gap: 10px; border-radius: 6px; padding: 0 10px; font-size: 13px; }
.rowMenuInline button:hover { background: var(--hover); color: var(--text); }
.rowMenuInline button.danger { color: var(--danger); }
.rowMenuInline button.danger:hover { background: var(--danger-soft); }

.pagination { display: flex; align-items: center; gap: 10px; margin-top: 14px; justify-content: flex-end; }
.pageInfo { color: var(--muted); margin-right: auto; font-size: 12px; }
.pageBtn { height: 32px; min-width: 32px; border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); color: var(--text-2); }
.pageBtn:hover:not(:disabled) { background: var(--hover); }
.pageBtn.active { border-color: var(--accent); color: var(--accent-contrast); background: var(--accent); font-weight: 600; }
.pageBtn:disabled { opacity: .4; cursor: not-allowed; }
.pageSelect { height: 32px; border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); color: var(--text-2); padding: 0 8px; }

.details {
  position: fixed; left: var(--sidebar); right: 0; bottom: 0; height: 30vh; min-height: 228px;
  background: var(--panel); border-top: 1px solid var(--line);
  box-shadow: 0 -8px 28px rgba(16, 24, 40, .10); z-index: 18; padding: 22px 28px;
  transform: translateY(100%); transition: transform .18s ease;
}
.details.open { transform: translateY(0); }
.detailsTop { display: flex; align-items: center; margin-bottom: 18px; }
.detailsId { font-size: 18px; font-weight: 650; color: var(--accent); font-family: var(--mono); }
.detailsActions { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.xbtn { border: 0; background: transparent; color: var(--muted); font-size: 24px; line-height: 1; }
.xbtn:hover { color: var(--text); }
.detailCols { display: grid; grid-template-columns: 1fr 1fr; gap: 56px; max-width: 700px; }
.kv { margin-bottom: 16px; }
.kv label { display: block; color: var(--muted); margin-bottom: 6px; font-size: .82rem; }
.err { color: var(--danger); }
</style>
