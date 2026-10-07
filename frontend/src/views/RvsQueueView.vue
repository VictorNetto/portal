<script setup>
import { ref, onMounted } from 'vue'
import { rvsQueue, setVulnRvs, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const items = ref([])
const loading = ref(true)
const error = ref('')
const rvsInputs = ref({})  // vulnId -> entered rvs id
const saving = ref({})

async function load() {
  loading.value = true; error.value = ''
  try { items.value = await rvsQueue() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao carregar' }
  finally { loading.value = false }
}

async function submit(v) {
  const rvs = (rvsInputs.value[v.id] || '').trim()
  if (!rvs) return
  saving.value = { ...saving.value, [v.id]: true }
  error.value = ''
  try {
    await setVulnRvs(v.id, rvs)
    delete rvsInputs.value[v.id]
    await load()
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : 'Falha ao registrar'
  } finally {
    saving.value = { ...saving.value, [v.id]: false }
  }
}

const sevClass = (s) => { const n = Number(s); return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo' }

onMounted(() => {
  document.documentElement.setAttribute('data-entity', 'vulns')
  load()
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('rvs.title') }}</h1>
        <p>{{ t('rvs.subtitle') }}</p>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>{{ t('cols.identifier') }}</th>
            <th>{{ t('cols.cvss') }}</th>
            <th>{{ t('rvs.dispatchedAt') }}</th>
            <th style="width:320px">{{ t('rvs.rvsId') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in items" :key="v.id">
            <td class="idcell">{{ v.internal_id }}</td>
            <td>{{ v.identifier || '—' }}</td>
            <td>
              <span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ v.cvss_score }}</span>
              <span v-else>—</span>
            </td>
            <td class="muted">{{ v.dispatched_at ? new Date(v.dispatched_at).toLocaleString() : '—' }}</td>
            <td>
              <form class="rvsForm" @submit.prevent="submit(v)">
                <input v-model="rvsInputs[v.id]" :placeholder="t('rvs.placeholder')" />
                <button class="btn primary" :disabled="saving[v.id] || !(rvsInputs[v.id] || '').trim()">
                  {{ t('rvs.enter') }}
                </button>
              </form>
            </td>
          </tr>
          <tr v-if="!loading && !items.length"><td colspan="5" class="empty">{{ t('rvs.empty') }}</td></tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<style scoped>
.pageTop { margin-bottom: 18px; }
.titleBlock h1 { margin: 0 0 4px; font-weight: 650; font-size: 24px; color: var(--text); letter-spacing: -.01em; }
.titleBlock p { margin: 0; color: var(--muted); font-size: 13px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; color: #7a8698; font-weight: 600; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; padding: 11px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
td { padding: 12px 16px; border-bottom: 1px solid var(--line); color: var(--text-2); font-size: 13px; }
tbody tr:last-child td { border-bottom: 0; }
.idcell { font-family: var(--mono); color: var(--accent); font-weight: 500; }
.cvss { font-family: var(--mono); font-weight: 700; }
.cvss.hi { color: var(--sev-hi); } .cvss.me { color: var(--sev-me); } .cvss.lo { color: var(--sev-lo); }
.rvsForm { display: flex; gap: 8px; }
.rvsForm input { flex: 1; background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: .45rem .6rem; color: var(--text); font-family: var(--mono); font-size: .88rem; }
.rvsForm input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.btn { border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); height: 34px; padding: 0 14px; color: var(--text-2); font-weight: 500; }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.empty { text-align: center; color: var(--muted); padding: 2.5rem; }
.muted { color: var(--muted); } .err { color: var(--danger); }
</style>
