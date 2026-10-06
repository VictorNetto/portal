<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getVuln, updateVuln, sendVuln, deleteVuln, ApiError } from '../api'

const route = useRoute()
const router = useRouter()
const id = route.params.id

const vuln = ref(null)
const form = ref({})
const loading = ref(true)
const error = ref('')
const notice = ref('')
const saving = ref(false)

// Field-lock rules mirrored from backend SPEC §4, for UX only (server enforces).
const editableFields = computed(() => {
  const s = vuln.value?.status
  if (s === 'draft' || s === 'saved_local') {
    return new Set(['identifier', 'cwe', 'description', 'finding_detail',
      'mitigation', 'cvss_score', 'cvss_vector', 'source', 'internal_notes'])
  }
  if (s === 'dispatching') return new Set()
  return new Set(['internal_notes']) // dispatched and beyond
})
const canEdit = (f) => editableFields.value.has(f)
const isDraft = computed(() => vuln.value?.status === 'draft')

function syncForm() {
  const v = vuln.value
  form.value = {
    identifier: v.identifier ?? '', cwe: v.cwe ?? '',
    description: v.description ?? '', finding_detail: v.finding_detail ?? '',
    mitigation: v.mitigation ?? '', cvss_score: v.cvss_score ?? '',
    cvss_vector: v.cvss_vector ?? '', source: v.source ?? '',
    internal_notes: v.internal_notes ?? '',
  }
}

async function load() {
  loading.value = true; error.value = ''
  try { vuln.value = await getVuln(id); syncForm() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Failed to load' }
  finally { loading.value = false }
}

async function save() {
  saving.value = true; error.value = ''; notice.value = ''
  try {
    const body = { version: vuln.value.version }
    for (const f of editableFields.value) {
      let val = form.value[f]
      if (f === 'cvss_score') val = val === '' ? null : Number(val)
      else val = val === '' ? null : val
      body[f] = val
    }
    vuln.value = await updateVuln(id, body)
    syncForm()
    notice.value = 'Saved.'
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      error.value = e.detail + ' (reloading…)'
      await load() // D5: reload to latest version so the user can reapply
    } else {
      error.value = e instanceof ApiError ? e.detail : 'Save failed'
    }
  } finally { saving.value = false }
}

async function doSend() {
  error.value = ''; notice.value = ''
  try { vuln.value = await sendVuln(id); syncForm(); notice.value = 'Sent — internal ID assigned.' }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Send failed' }
}

async function remove() {
  if (!confirm('Delete this vulnerability?')) return
  try { await deleteVuln(id); router.push('/') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Delete failed' }
}

onMounted(load)
</script>

<template>
  <main class="detail-wrap">
  <section class="panel" v-if="vuln">
    <div class="head">
      <div>
        <h2>{{ vuln.internal_id || 'Draft vulnerability' }}</h2>
        <span class="status">{{ vuln.status }} · v{{ vuln.version }}</span>
      </div>
      <div class="actions">
        <button v-if="isDraft" class="go" @click="doSend">Send</button>
        <button class="danger" @click="remove">Delete</button>
        <button class="ghost" @click="router.push('/')">Back</button>
      </div>
    </div>

    <p v-if="!editableFields.size" class="locked">
      This vulnerability is locked in status “{{ vuln.status }}” — no fields are editable.
    </p>

    <div class="grid">
      <label>Identifier</label>
      <input v-model="form.identifier" :disabled="!canEdit('identifier')" />
      <label>CWE</label>
      <input v-model="form.cwe" :disabled="!canEdit('cwe')" />
      <label>CVSS score</label>
      <input v-model="form.cvss_score" type="number" step="0.1" min="0" max="10" :disabled="!canEdit('cvss_score')" />
      <label>CVSS vector</label>
      <input v-model="form.cvss_vector" :disabled="!canEdit('cvss_vector')" />
      <label>Source</label>
      <input v-model="form.source" :disabled="!canEdit('source')" />
      <label>Description</label>
      <textarea v-model="form.description" :disabled="!canEdit('description')" rows="3" />
      <label>Finding detail</label>
      <textarea v-model="form.finding_detail" :disabled="!canEdit('finding_detail')" rows="3" />
      <label>Mitigation</label>
      <textarea v-model="form.mitigation" :disabled="!canEdit('mitigation')" rows="3" />
      <label>Internal notes</label>
      <textarea v-model="form.internal_notes" :disabled="!canEdit('internal_notes')" rows="2" />
    </div>

    <div class="footer">
      <button class="go" :disabled="saving || !editableFields.size" @click="save">
        {{ saving ? 'Saving…' : 'Save' }}
      </button>
      <span v-if="notice" class="ok">{{ notice }}</span>
      <span v-if="error" class="err">{{ error }}</span>
    </div>
  </section>
  <p v-else-if="loading" class="muted">Loading…</p>
  <p v-else class="err">{{ error }}</p>
  </main>
</template>

<style scoped>
.detail-wrap { padding: 2rem; max-width: 920px; margin: 0 auto; }
.panel { background: #0f1620; border: 1px solid #1f2933; border-radius: 10px; padding: 1.2rem 1.4rem; }
.head { display: flex; justify-content: space-between; align-items: flex-start; }
h2 { margin: 0; font-size: 1.05rem; }
.status { color: #7d8ea3; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
.actions { display: flex; gap: .5rem; }
.locked { background: #241a0c; border: 1px solid #b45309; color: #fbbf24; padding: .6rem .8rem; border-radius: 6px; }
.grid { display: grid; grid-template-columns: max-content 1fr; gap: .6rem 1rem; align-items: start; margin: 1.2rem 0; }
label { color: #9fb0c3; font-size: .82rem; padding-top: .5rem; }
input, textarea { background: #0b0f14; border: 1px solid #1f2933; border-radius: 6px; padding: .5rem .6rem; color: #e6edf3; font: inherit; width: 100%; }
input:disabled, textarea:disabled { opacity: .45; cursor: not-allowed; }
textarea { resize: vertical; }
.footer { display: flex; align-items: center; gap: 1rem; }
button { padding: .5rem 1rem; border: 0; border-radius: 6px; font-weight: 600; cursor: pointer; }
button.go { background: #2563eb; color: #fff; }
button.ghost { background: transparent; border: 1px solid #1f2933; color: #cbd5e1; }
button.danger { background: #7f1d1d; color: #fecaca; }
button:disabled { opacity: .5; cursor: not-allowed; }
.ok { color: #4ade80; } .err { color: #f87171; } .muted { color: #7d8ea3; }
</style>
