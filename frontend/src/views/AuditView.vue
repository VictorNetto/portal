<script setup>
import { ref, computed, onMounted } from 'vue'
import { listAudit, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const data = ref({ items: [], total: 0, page: 1, page_size: 25 })
const loading = ref(true)
const error = ref('')
const actionFilter = ref('')

const ACTIONS = [
  'login', 'logout', 'create', 'read', 'update', 'delete', 'status_change',
  'export', 'dispatch', 'api_key_create', 'api_key_revoke', 'permission_change',
  'lock_override', 'correction',
]

const page = ref(1)
const pageCount = computed(() => Math.max(1, Math.ceil(data.value.total / data.value.page_size)))

async function load() {
  loading.value = true; error.value = ''
  try {
    data.value = await listAudit({ page: page.value, page_size: 25, action: actionFilter.value })
  } catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao carregar' }
  finally { loading.value = false }
}

function applyFilter() { page.value = 1; load() }
function go(n) { page.value = n; load() }

function fmtDetail(d) {
  if (!d) return '—'
  return Object.entries(d).map(([k, v]) =>
    `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join('  ')
}

// Color actions by rough category for quick scanning.
const actionClass = (a) => {
  if (['delete', 'api_key_revoke'].includes(a)) return 'danger'
  if (['create', 'api_key_create', 'dispatch'].includes(a)) return 'good'
  if (['permission_change', 'correction', 'lock_override', 'status_change'].includes(a)) return 'warn'
  return 'neutral'
}

onMounted(() => { document.documentElement.removeAttribute('data-entity'); load() })
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('audit.title') }}</h1>
        <p>{{ t('audit.subtitle') }}</p>
      </div>
      <select class="filterSel" v-model="actionFilter" @change="applyFilter">
        <option value="">{{ t('audit.allActions') }}</option>
        <option v-for="a in ACTIONS" :key="a" :value="a">{{ a }}</option>
      </select>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th style="width:170px">{{ t('audit.when') }}</th>
            <th style="width:120px">{{ t('audit.actor') }}</th>
            <th style="width:150px">{{ t('audit.action') }}</th>
            <th style="width:100px">{{ t('audit.entity') }}</th>
            <th style="width:120px">{{ t('audit.ip') }}</th>
            <th>{{ t('audit.detail') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in data.items" :key="e.id">
            <td class="mono dim">{{ new Date(e.created_at).toLocaleString() }}</td>
            <td class="actor">{{ e.actor }}</td>
            <td><span class="act" :class="actionClass(e.action)">{{ e.action }}</span></td>
            <td class="dim">{{ e.entity_type || '—' }}</td>
            <td class="mono dim">{{ e.ip_address || '—' }}</td>
            <td class="mono detail">{{ fmtDetail(e.detail) }}</td>
          </tr>
          <tr v-if="!loading && !data.items.length"><td colspan="6" class="empty">{{ t('audit.empty') }}</td></tr>
        </tbody>
      </table>
    </section>

    <div class="pagination">
      <span class="pageInfo mono">{{ data.total }} registros</span>
      <button class="pageBtn" :disabled="page <= 1" @click="go(page - 1)">‹</button>
      <span class="pageInfo mono">{{ page }} / {{ pageCount }}</span>
      <button class="pageBtn" :disabled="page >= pageCount" @click="go(page + 1)">›</button>
    </div>
  </AppShell>
</template>

<style scoped>
.pageTop { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.titleBlock h1 { margin: 0 0 4px; font-weight: 650; font-size: 24px; color: var(--text); letter-spacing: -.01em; }
.titleBlock p { margin: 0; color: var(--muted); font-size: 13px; }
.filterSel { height: 36px; border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); color: var(--text-2); padding: 0 10px; }
.filterSel:focus { outline: none; border-color: var(--accent); }

.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th { text-align: left; color: #7a8698; font-weight: 600; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; padding: 10px 14px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
td { padding: 9px 14px; border-bottom: 1px solid var(--line); color: var(--text-2); font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
tbody tr:last-child td { border-bottom: 0; }
.mono { font-family: var(--mono); }
.dim { color: var(--muted); }
.actor { font-weight: 500; color: var(--text); }
.detail { color: var(--text-2); }
.act { font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600; font-family: var(--mono); }
.act.neutral { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.act.good { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }
.act.warn { color: var(--st-wait-fg); background: var(--st-wait-bg); }
.act.danger { color: var(--danger); background: var(--danger-soft); }
.empty { text-align: center; color: var(--muted); padding: 2.5rem; white-space: normal; }

.pagination { display: flex; align-items: center; gap: 14px; margin-top: 14px; justify-content: flex-end; }
.pageInfo { color: var(--muted); font-size: 12px; }
.pageInfo:first-child { margin-right: auto; }
.pageBtn { height: 32px; min-width: 32px; border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); color: var(--text-2); }
.pageBtn:hover:not(:disabled) { background: var(--hover); }
.pageBtn:disabled { opacity: .4; cursor: not-allowed; }
.err { color: var(--danger); }
</style>
