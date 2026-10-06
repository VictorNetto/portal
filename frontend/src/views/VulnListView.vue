<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listVulns, createVuln } from '../api'
import { ApiError } from '../api'

const router = useRouter()
const vulns = ref([])
const loading = ref(true)
const error = ref('')

const showCreate = ref(false)
const draft = ref({ identifier: '', description: '', cvss_score: null })
const creating = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    vulns.value = await listVulns()
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : 'Failed to load'
  } finally {
    loading.value = false
  }
}

async function create() {
  creating.value = true
  error.value = ''
  try {
    const body = {
      identifier: draft.value.identifier || null,
      description: draft.value.description || null,
      cvss_score: draft.value.cvss_score !== null && draft.value.cvss_score !== ''
        ? Number(draft.value.cvss_score) : null,
    }
    const v = await createVuln(body)
    showCreate.value = false
    draft.value = { identifier: '', description: '', cvss_score: null }
    router.push(`/vulns/${v.id}`)
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : 'Failed to create'
  } finally {
    creating.value = false
  }
}

const statusColor = (s) => ({
  draft: '#64748b', saved_local: '#3b82f6', dispatching: '#f59e0b',
  dispatched: '#8b5cf6', acknowledged: '#06b6d4', waiting_fix: '#f97316',
  pending_retest: '#eab308', fixed: '#22c55e',
}[s] || '#64748b')

onMounted(load)
</script>

<template>
  <section class="panel">
    <div class="head">
      <h2>Vulnerabilities</h2>
      <button @click="showCreate = !showCreate">
        {{ showCreate ? 'Cancel' : '+ New vulnerability' }}
      </button>
    </div>

    <form v-if="showCreate" class="create" @submit.prevent="create">
      <input v-model="draft.identifier" placeholder="Identifier (CVE or name) — optional" />
      <input v-model="draft.description" placeholder="Short description" />
      <input v-model="draft.cvss_score" type="number" step="0.1" min="0" max="10"
             placeholder="CVSS" style="max-width:90px" />
      <button :disabled="creating">Create draft</button>
    </form>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="loading" class="muted">Loading…</p>

    <table v-else-if="vulns.length">
      <thead>
        <tr><th>ID</th><th>Status</th><th>Identifier</th><th>CVSS</th><th>Updated</th></tr>
      </thead>
      <tbody>
        <tr v-for="v in vulns" :key="v.id" @click="router.push(`/vulns/${v.id}`)">
          <td>{{ v.internal_id || '—' }}</td>
          <td><span class="badge" :style="{ background: statusColor(v.status) }">{{ v.status }}</span></td>
          <td>{{ v.identifier || '—' }}</td>
          <td>{{ v.cvss_score ?? '—' }}</td>
          <td class="muted">{{ new Date(v.updated_at).toLocaleString() }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">No vulnerabilities yet.</p>
  </section>
</template>

<style scoped>
.panel { background: #0f1620; border: 1px solid #1f2933; border-radius: 10px; padding: 1.2rem 1.4rem; }
.head { display: flex; align-items: center; justify-content: space-between; }
h2 { margin: 0; font-size: 1rem; }
button { padding: .45rem .9rem; border: 0; border-radius: 6px; background: #2563eb; color: #fff; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .5; }
.create { display: flex; gap: .6rem; margin: 1rem 0; flex-wrap: wrap; }
.create input { flex: 1; min-width: 140px; background: #0b0f14; border: 1px solid #1f2933; border-radius: 6px; padding: .5rem .6rem; color: #e6edf3; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th { text-align: left; color: #7d8ea3; font-weight: 500; font-size: .8rem; padding: .4rem .5rem; border-bottom: 1px solid #1f2933; }
td { padding: .55rem .5rem; border-bottom: 1px solid #141b24; font-size: .9rem; }
tbody tr { cursor: pointer; }
tbody tr:hover { background: #121a24; }
.badge { padding: .1rem .5rem; border-radius: 999px; font-size: .72rem; color: #fff; text-transform: uppercase; letter-spacing: .03em; }
.muted { color: #7d8ea3; } .err { color: #f87171; }
</style>
