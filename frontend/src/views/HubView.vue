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
const query = ref('')
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

const statusColor = (s) => ({
  draft: '#8fa49a', saved_local: 'var(--blue)', dispatching: 'var(--amber)',
  dispatched: 'var(--purple)', acknowledged: 'var(--blue)', waiting_fix: 'var(--amber)',
  pending_retest: 'var(--amber)', fixed: 'var(--green)',
}[s] || 'var(--muted)')

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
      <div class="toolbar">
        <FilterBar ref="filterBar" v-model="query" />
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
              <td class="val" @click="openPreview(v)">{{ v.identifier || '—' }}</td>
              <td @click="openPreview(v)">
                <span class="pill" :style="{ color: statusColor(v.status) }">{{ v.status }}</span>
              </td>
              <td @click="openPreview(v)">{{ v.cvss_score ?? '—' }}</td>
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
              <span class="pill" :style="{ color: statusColor(preview.status) }">{{ preview.status }}</span></div>
            <div class="kv"><label>{{ t('cols.cvss') }}</label><span>{{ preview.cvss_score ?? '—' }}</span></div>
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
.titleBlock h1 { margin: 0 0 6px; font-weight: 500; font-size: 28px; color: #f0fff6; }
.titleBlock p { margin: 0; color: var(--muted); }

.hubTop { display: flex; align-items: end; margin-bottom: 16px; gap: 18px; }
.tabs { display: flex; gap: 24px; align-items: center; }
.tab { border: 0; background: transparent; color: var(--muted); padding: 12px 0 11px; font-size: 16px; border-bottom: 2px solid transparent; }
.tab.active { color: var(--green); border-color: var(--green); }
.toolbar { margin-left: auto; display: flex; gap: 12px; align-items: center; }
.selectionHint { color: var(--muted); font-size: 12px; align-self: center; }

.btn {
  border: 1px solid var(--line2); background: #071512; border-radius: 6px; height: 38px;
  padding: 0 16px; color: var(--text); display: inline-flex; align-items: center; gap: 9px;
}
.btn:hover { border-color: var(--green); color: var(--green); }
.btn.primary { background: linear-gradient(180deg, #48df7d, #2fbf68); border-color: #4df587; color: #03120a; font-weight: 600; }
.btn.primary:hover { color: #03120a; }
.create { width: 210px; justify-content: center; white-space: nowrap; }

.panel { background: rgba(7, 19, 17, .82); border: 1px solid rgba(65, 110, 91, .45); border-radius: var(--radius); }
.stub { padding: 3rem; text-align: center; color: var(--muted); }
.tablePanel { overflow: auto; }

table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th:nth-child(1), td:nth-child(1) { width: 54px; }
th:nth-child(2), td:nth-child(2) { width: 220px; }
th:nth-child(3), td:nth-child(3) { width: 150px; }
th:nth-child(4), td:nth-child(4) { width: 90px; }
th:nth-child(5), td:nth-child(5) { width: 220px; }
th:nth-child(6), td:nth-child(6) { width: 160px; }
th:nth-child(7), td:nth-child(7) { width: 82px; }
.val { overflow: hidden; text-overflow: ellipsis; }
th, td { text-align: left; border-bottom: 1px solid rgba(54, 92, 82, .42); padding: 13px 18px; white-space: nowrap; }
th { color: #e7f7ed; font-weight: 500; background: rgba(5, 15, 14, .55); }
td { color: #d9e8df; cursor: pointer; }
tr:hover { background: rgba(66, 230, 123, .045); }
tr.preview { background: linear-gradient(90deg, rgba(66, 230, 123, .12), rgba(66, 230, 123, .035)); }
tr.selected { background: rgba(66, 230, 123, .08); }
.check { width: 18px; height: 18px; accent-color: var(--green); }
.pill { display: inline-flex; align-items: center; border-radius: 5px; border: 1px solid currentColor; padding: 3px 9px; font-size: 12px; }
.empty { text-align: center; color: var(--muted); cursor: default; padding: 2.5rem; }

.rowActionWrap { position: relative; display: inline-flex; justify-content: center; }
.kebab { border: 0; background: transparent; font-size: 22px; color: var(--muted); padding: 2px 8px; }
.rowMenuInline {
  position: absolute; right: 0; top: 30px; min-width: 170px; border: 1px solid rgba(65, 110, 91, .62);
  background: #071211; border-radius: 8px; box-shadow: var(--shadow); padding: 8px; z-index: 50; text-align: left;
}
.rowMenuInline button { width: 100%; height: 36px; border: 0; background: transparent; color: var(--text); display: flex; align-items: center; gap: 10px; border-radius: 6px; padding: 0 10px; }
.rowMenuInline button:hover { background: rgba(66, 230, 123, .10); color: var(--green); }
.rowMenuInline button.danger { color: #ff8d83; }
.rowMenuInline button.danger:hover { background: rgba(255, 107, 95, .10); color: var(--red); }

.pagination { display: flex; align-items: center; gap: 10px; margin-top: 14px; justify-content: flex-end; }
.pageInfo { color: var(--muted); margin-right: auto; font-size: 12px; }
.pageBtn { height: 34px; min-width: 34px; border: 1px solid var(--line2); background: #071512; border-radius: 6px; color: var(--text); }
.pageBtn.active { border-color: var(--green); color: #03120a; background: var(--green); font-weight: 700; }
.pageBtn:disabled { opacity: .35; cursor: not-allowed; }
.pageSelect { height: 34px; border: 1px solid var(--line2); background: #071512; border-radius: 6px; color: var(--text); padding: 0 10px; }

.details {
  position: fixed; left: var(--sidebar); right: 0; bottom: 0; height: 30vh; min-height: 228px;
  background: rgba(7, 18, 17, .985); border-top: 1px solid rgba(65, 110, 91, .50);
  box-shadow: 0 -18px 48px rgba(0, 0, 0, .44); z-index: 18; padding: 22px 28px;
  transform: translateY(100%); transition: transform .18s ease;
}
.details.open { transform: translateY(0); }
.detailsTop { display: flex; align-items: center; margin-bottom: 18px; }
.detailsId { font-size: 22px; color: var(--green); }
.detailsActions { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.xbtn { border: 0; background: transparent; color: #c9d8d1; font-size: 26px; line-height: 1; }
.detailCols { display: grid; grid-template-columns: 1fr 1fr; gap: 56px; max-width: 700px; }
.kv { margin-bottom: 16px; }
.kv label { display: block; color: var(--muted); margin-bottom: 6px; font-size: .85rem; }
.err { color: var(--red); }
</style>
