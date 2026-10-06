<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getVuln, createVuln, updateVuln, sendVuln, deleteVuln, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'vuln-new')
const id = route.params.id

const vuln = ref(null)
const form = ref({
  identifier: '', cwe: '', description: '', finding_detail: '',
  mitigation: '', cvss_score: '', cvss_vector: '', source: '', internal_notes: '',
})
const loading = ref(!isNew.value)
const saving = ref(false)
const error = ref('')
const notice = ref('')

// Field-lock rules (SPEC §4), mirrored for UX; server enforces regardless.
const editableFields = computed(() => {
  if (isNew.value) return new Set(Object.keys(form.value))
  const s = vuln.value?.status
  if (s === 'draft' || s === 'saved_local')
    return new Set(['identifier', 'cwe', 'description', 'finding_detail',
      'mitigation', 'cvss_score', 'cvss_vector', 'source', 'internal_notes'])
  if (s === 'dispatching') return new Set()
  return new Set(['internal_notes'])
})
const canEdit = (f) => editableFields.value.has(f)
const isDraft = computed(() => isNew.value || vuln.value?.status === 'draft')

function syncForm() {
  const v = vuln.value
  for (const k of Object.keys(form.value)) form.value[k] = v[k] ?? ''
}

async function load() {
  if (isNew.value) return
  loading.value = true; error.value = ''
  try { vuln.value = await getVuln(id); syncForm() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao carregar' }
  finally { loading.value = false }
}

function bodyFromForm(fields) {
  const body = {}
  for (const f of fields) {
    let val = form.value[f]
    if (f === 'cvss_score') val = val === '' ? null : Number(val)
    else val = val === '' ? null : val
    body[f] = val
  }
  return body
}

async function save() {
  saving.value = true; error.value = ''; notice.value = ''
  try {
    if (isNew.value) {
      const created = await createVuln(bodyFromForm(Object.keys(form.value)))
      router.replace(`/vulnerabilities/${created.id}`)
      return
    }
    const body = { version: vuln.value.version, ...bodyFromForm([...editableFields.value]) }
    vuln.value = await updateVuln(id, body); syncForm(); notice.value = 'Salvo.'
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) { error.value = e.detail; await load() }
    else error.value = e instanceof ApiError ? e.detail : 'Falha ao salvar'
  } finally { saving.value = false }
}

async function doSend() {
  error.value = ''; notice.value = ''
  try { vuln.value = await sendVuln(id); syncForm(); notice.value = 'Enviado — ID interno atribuído.' }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao enviar' }
}

async function remove() {
  if (!confirm('Excluir esta vulnerabilidade?')) return
  try { await deleteVuln(id); router.push('/hub') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao excluir' }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1 class="mono">
          {{ isNew ? t('hub.createVuln') : (vuln?.internal_id || t('cols.identifier')) }}
        </h1>
        <p v-if="vuln">{{ vuln.status }} · v{{ vuln.version }}</p>
        <p v-else-if="isNew">Rascunho novo</p>
      </div>
      <div class="pageActions">
        <button v-if="!isNew && isDraft" class="btn primary" @click="doSend">↗ {{ t('rowActions.send') }}</button>
        <button v-if="!isNew" class="btn danger" @click="remove">⌫ {{ t('rowActions.delete') }}</button>
        <button class="btn" @click="router.push('/hub')">‹ {{ t('nav.hub') }}</button>
      </div>
    </div>

    <section class="panel editor">
      <p v-if="loading" class="muted">Carregando…</p>
      <template v-else>
        <p v-if="!editableFields.size" class="locked">
          Bloqueada no status “{{ vuln.status }}” — nenhum campo é editável.
        </p>

        <div class="grid">
          <label>{{ t('cols.identifier') }}</label>
          <input v-model="form.identifier" :disabled="!canEdit('identifier')" />
          <label>CWE</label>
          <input v-model="form.cwe" :disabled="!canEdit('cwe')" />
          <label>{{ t('cols.cvss') }}</label>
          <input v-model="form.cvss_score" type="number" step="0.1" min="0" max="10" :disabled="!canEdit('cvss_score')" />
          <label>CVSS vector</label>
          <input v-model="form.cvss_vector" :disabled="!canEdit('cvss_vector')" />
          <label>{{ t('cols.source') }}</label>
          <input v-model="form.source" :disabled="!canEdit('source')" />
          <label>Descrição</label>
          <textarea v-model="form.description" rows="3" :disabled="!canEdit('description')" />
          <label>Detalhe do achado</label>
          <textarea v-model="form.finding_detail" rows="3" :disabled="!canEdit('finding_detail')" />
          <label>Mitigação</label>
          <textarea v-model="form.mitigation" rows="3" :disabled="!canEdit('mitigation')" />
          <label>Notas internas</label>
          <textarea v-model="form.internal_notes" rows="2" :disabled="!canEdit('internal_notes')" />
        </div>

        <div class="footer">
          <button class="btn primary" :disabled="saving || !editableFields.size" @click="save">
            {{ saving ? 'Salvando…' : (isNew ? 'Criar rascunho' : 'Salvar') }}
          </button>
          <span v-if="notice" class="ok">{{ notice }}</span>
          <span v-if="error" class="err">{{ error }}</span>
        </div>
      </template>
    </section>
  </AppShell>
</template>

<style scoped>
.pageTop { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.titleBlock h1 { margin: 0 0 6px; font-weight: 500; font-size: 26px; color: #f0fff6; }
.titleBlock p { margin: 0; color: var(--muted); text-transform: uppercase; font-size: .8rem; letter-spacing: .04em; }
.pageActions { display: flex; gap: 10px; }

.btn { border: 1px solid var(--line2); background: #071512; border-radius: 6px; height: 38px; padding: 0 16px; color: var(--text); display: inline-flex; align-items: center; gap: 8px; }
.btn:hover { border-color: var(--green); color: var(--green); }
.btn.primary { background: linear-gradient(180deg, #48df7d, #2fbf68); border-color: #4df587; color: #03120a; font-weight: 600; }
.btn.primary:hover { color: #03120a; }
.btn.danger { color: #ff8d83; }
.btn.danger:hover { border-color: var(--red); color: var(--red); }
.btn:disabled { opacity: .5; cursor: not-allowed; }

.panel { background: rgba(7, 19, 17, .82); border: 1px solid rgba(65, 110, 91, .45); border-radius: var(--radius); }
.editor { padding: 1.4rem 1.6rem; max-width: 820px; }
.locked { background: #241a0c; border: 1px solid rgba(245, 167, 66, .5); color: var(--amber); padding: .6rem .8rem; border-radius: 6px; }
.grid { display: grid; grid-template-columns: max-content 1fr; gap: .7rem 1.2rem; align-items: start; margin-bottom: 1.4rem; }
label { color: var(--muted); font-size: .85rem; padding-top: .5rem; }
input, textarea { background: #0b0f14; border: 1px solid var(--line); border-radius: 6px; padding: .5rem .65rem; color: var(--text); width: 100%; font-family: var(--mono); font-size: .9rem; }
input:focus, textarea:focus { outline: none; border-color: var(--green); }
input:disabled, textarea:disabled { opacity: .45; cursor: not-allowed; }
textarea { resize: vertical; }
.footer { display: flex; align-items: center; gap: 1rem; }
.ok { color: var(--green); } .err { color: var(--red); } .muted { color: var(--muted); }
</style>
