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
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
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
      <select v-model="actionFilter" @change="applyFilter">
        <option value="">{{ t('audit.allActions') }}</option>
        <option v-for="a in ACTIONS" :key="a" :value="a">{{ a }}</option>
      </select>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th style="width:200px">{{ t('audit.when') }}</th>
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
      <span class="pageInfo mono">{{ data.total }} {{ t('misc.records') }}</span>
      <button class="pageBtn" :disabled="page <= 1" @click="go(page - 1)">{{ t('common.prev') }}</button>
      <span class="pageInfo mono">{{ page }} / {{ pageCount }}</span>
      <button class="pageBtn" :disabled="page >= pageCount" @click="go(page + 1)">{{ t('common.next') }}</button>
    </div>
  </AppShell>
</template>

<style scoped>
table { table-layout: fixed; }
td { padding: 9px 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12.5px; }
th { padding: 10px 14px; }
.dim { color: var(--muted); }
.actor { color: var(--text); }
.act { font-size: 11px; padding: 2px 8px; border-radius: var(--radius-sm); font-family: var(--mono); }
.act.neutral { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.act.good { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }
.act.warn { color: var(--st-wait-fg); background: var(--st-wait-bg); }
.act.danger { color: var(--danger); background: var(--danger-soft); }
</style>
