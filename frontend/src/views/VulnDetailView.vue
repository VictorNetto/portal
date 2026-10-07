<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getVuln, createVuln, updateVuln, sendVuln, deleteVuln, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'vuln-new')

// This is always a vulnerability view -> green accent.
document.documentElement.setAttribute('data-entity', 'vulns')
onUnmounted(() => document.documentElement.removeAttribute('data-entity'))
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
        <span class="ctxchip"><span class="dot"></span>Vulnerabilidade</span>
        <h1>
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
.ctxchip { display: inline-flex; align-items: center; gap: 7px; padding: 4px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-size: 12px; font-weight: 600; margin-bottom: 10px; }
.ctxchip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); }
.titleBlock h1 { margin: 0 0 4px; font-weight: 650; font-size: 22px; color: var(--text); font-family: var(--mono); letter-spacing: -.01em; }
.titleBlock p { margin: 0; color: var(--muted); text-transform: uppercase; font-size: .78rem; letter-spacing: .04em; }
.pageActions { display: flex; gap: 10px; }

.btn { border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); height: 36px; padding: 0 14px; color: var(--text-2); display: inline-flex; align-items: center; gap: 8px; font-weight: 500; }
.btn:hover { border-color: var(--dim); background: var(--hover); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; box-shadow: var(--shadow); }
.btn.primary:hover { filter: brightness(1.05); }
.btn.danger { color: var(--danger); }
.btn.danger:hover { border-color: var(--danger); background: var(--danger-soft); }
.btn:disabled { opacity: .5; cursor: not-allowed; }

.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
.editor { padding: 1.5rem 1.7rem; max-width: 820px; }
.locked { background: var(--st-wait-bg); border: 1px solid #fde68a; color: var(--st-wait-fg); padding: .6rem .8rem; border-radius: var(--radius-sm); }
.grid { display: grid; grid-template-columns: max-content 1fr; gap: .8rem 1.4rem; align-items: start; margin-bottom: 1.4rem; }
label { color: var(--muted); font-size: .85rem; padding-top: .5rem; }
input, textarea { background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: .5rem .65rem; color: var(--text); width: 100%; font-family: var(--mono); font-size: .9rem; }
input:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
input:disabled, textarea:disabled { background: var(--panel-2); color: var(--muted); cursor: not-allowed; }
textarea { resize: vertical; }
.footer { display: flex; align-items: center; gap: 1rem; }
.ok { color: var(--accent); } .err { color: var(--danger); } .muted { color: var(--muted); }
</style>
