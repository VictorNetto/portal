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
.rvsForm { display: flex; gap: 8px; }
.rvsForm input { flex: 1; font-family: var(--mono); font-size: 13px; }
</style>
