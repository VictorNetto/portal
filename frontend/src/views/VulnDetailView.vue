<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getVuln, createVuln, updateVuln, sendVuln, dispatchVuln, deleteVuln, listUsers, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const route = useRoute()
const router = useRouter()
const isNew = computed(() => route.name === 'vuln-new')

// This is always a vulnerability view -> green accent.
document.documentElement.setAttribute('data-entity', 'vulns')
onUnmounted(() => document.documentElement.removeAttribute('data-entity'))

// `id` is reactive: creating a vuln then router.replace()ing to its detail
// reuses this component, so we reload when the route changes rather than only
// on mount.
const id = computed(() => route.params.id)

const vuln = ref(null)
const form = ref({
  identifier: '', cwe: '', description: '', finding_detail: '',
  mitigation: '', cvss_score: '', cvss_vector: '', source: '', internal_notes: '',
})
const loading = ref(!isNew.value)
const saving = ref(false)
const error = ref('')
const notice = ref('')

// Operators
const allUsers = ref([])
const selectedOps = ref(new Set())  // user ids

// Field-lock rules (SPEC §4), mirrored for UX; server enforces regardless.
// `operators` is an assignment, editable except while dispatching.
const editableFields = computed(() => {
  if (isNew.value) return new Set([...Object.keys(form.value), 'operators'])
  const s = vuln.value?.status
  if (s === 'draft' || s === 'saved_local')
    return new Set(['identifier', 'cwe', 'description', 'finding_detail',
      'mitigation', 'cvss_score', 'cvss_vector', 'source', 'internal_notes', 'operators'])
  if (s === 'dispatching') return new Set()
  return new Set(['internal_notes', 'operators'])
})
const canEdit = (f) => editableFields.value.has(f)
const isDraft = computed(() => isNew.value || vuln.value?.status === 'draft')

function syncForm() {
  const v = vuln.value
  for (const k of Object.keys(form.value)) form.value[k] = v[k] ?? ''
  selectedOps.value = new Set((v.operators || []).map((o) => o.id))
}

function toggleOp(uid) {
  if (!canEdit('operators')) return
  if (selectedOps.value.has(uid)) selectedOps.value.delete(uid)
  else selectedOps.value.add(uid)
  selectedOps.value = new Set(selectedOps.value)
}

async function load() {
  // load users for the picker regardless (new or edit)
  try { allUsers.value = await listUsers() } catch { /* non-fatal */ }
  if (isNew.value) return
  loading.value = true; error.value = ''
  try { vuln.value = await getVuln(id.value); syncForm() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

function bodyFromForm(fields) {
  const body = {}
  for (const f of fields) {
    if (f === 'operators') continue // handled separately as operator_ids
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
      const body = bodyFromForm(Object.keys(form.value))
      body.operator_ids = [...selectedOps.value]
      const created = await createVuln(body)
      router.replace(`/vulnerabilities/${created.id}`)
      return
    }
    const body = { version: vuln.value.version, ...bodyFromForm([...editableFields.value]) }
    if (canEdit('operators')) body.operator_ids = [...selectedOps.value]
    vuln.value = await updateVuln(id.value, body); syncForm(); notice.value = t('vuln.saved')
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) { error.value = e.detail; await load() }
    else error.value = e instanceof ApiError ? e.detail : t('errors.save')
  } finally { saving.value = false }
}

async function doSend() {
  error.value = ''; notice.value = ''
  try { vuln.value = await sendVuln(id.value); syncForm(); notice.value = t('vuln.sent') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.send') }
}

const isSavedLocal = computed(() => vuln.value?.status === 'saved_local')
async function doDispatch() {
  if (!confirm(t('vuln.confirmDispatch'))) return
  error.value = ''; notice.value = ''
  try { vuln.value = await dispatchVuln(id.value); syncForm(); notice.value = t('vuln.dispatched') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.dispatch') }
}

async function remove() {
  if (!confirm(t('vuln.confirmDelete'))) return
  try { await deleteVuln(id.value); router.push('/hub') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

onMounted(load)
// Reload when navigating between new -> created detail (same component reused).
watch(() => route.fullPath, () => load())
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <span class="ctxchip">{{ t('vuln.chip') }}</span>
        <h1 :class="{ mono: !isNew }">
          {{ isNew ? t('hub.createVuln') : (vuln?.internal_id || t('cols.identifier')) }}
        </h1>
        <p v-if="vuln">{{ t('status.' + vuln.status) }} · v{{ vuln.version }}</p>
        <p v-else-if="isNew">{{ t('vuln.newDraft') }}</p>
      </div>
      <div class="pageActions">
        <button v-if="!isNew && isDraft" class="btn primary" @click="doSend">{{ t('rowActions.send') }}</button>
        <button v-if="isSavedLocal" class="btn primary" @click="doDispatch">{{ t('actions.dispatch') }}</button>
        <button v-if="!isNew" class="btn danger" @click="remove">{{ t('rowActions.delete') }}</button>
        <button class="btn" @click="router.push('/hub')">{{ t('nav.hub') }}</button>
      </div>
    </div>

    <section class="panel editor">
      <p v-if="loading" class="muted">{{ t('vuln.loading') }}</p>
      <template v-else>
        <p v-if="!editableFields.size" class="locked">
          {{ t('vuln.locked', { status: t('status.' + vuln.status) }) }}
        </p>

        <div class="grid">
          <label>{{ t('cols.identifier') }}</label>
          <input v-model="form.identifier" :disabled="!canEdit('identifier')" />
          <label>{{ t('vuln.cwe') }}</label>
          <input v-model="form.cwe" :disabled="!canEdit('cwe')" />
          <label>{{ t('cols.cvss') }}</label>
          <input v-model="form.cvss_score" type="number" step="0.1" min="0" max="10" :disabled="!canEdit('cvss_score')" />
          <label>{{ t('vuln.cvssVector') }}</label>
          <input v-model="form.cvss_vector" :disabled="!canEdit('cvss_vector')" />
          <label>{{ t('cols.source') }}</label>
          <input v-model="form.source" :disabled="!canEdit('source')" />
          <label>{{ t('cols.operators') }}</label>
          <div class="opchips" :class="{ locked: !canEdit('operators') }">
            <button v-for="u in allUsers" :key="u.id" type="button" class="opchip"
                    :class="{ on: selectedOps.has(u.id) }"
                    :disabled="!canEdit('operators')" @click="toggleOp(u.id)">
              {{ u.username }}
            </button>
            <span v-if="!allUsers.length" class="muted">—</span>
          </div>
          <label>{{ t('vuln.description') }}</label>
          <textarea v-model="form.description" rows="3" :disabled="!canEdit('description')" />
          <label>{{ t('vuln.findingDetail') }}</label>
          <textarea v-model="form.finding_detail" rows="3" :disabled="!canEdit('finding_detail')" />
          <label>{{ t('vuln.mitigation') }}</label>
          <textarea v-model="form.mitigation" rows="3" :disabled="!canEdit('mitigation')" />
          <label>{{ t('vuln.internalNotes') }}</label>
          <textarea v-model="form.internal_notes" rows="2" :disabled="!canEdit('internal_notes')" />
        </div>

        <div class="footer">
          <button class="btn primary" :disabled="saving || !editableFields.size" @click="save">
            {{ saving ? t('vuln.saving') : (isNew ? t('vuln.createDraft') : t('vuln.save')) }}
          </button>
          <span v-if="notice" class="ok">{{ notice }}</span>
          <span v-if="error" class="err">{{ error }}</span>
        </div>
      </template>
    </section>
  </AppShell>
</template>

<style scoped>
.ctxchip { display: inline-block; padding: 2px 9px; border-radius: var(--radius-sm); background: var(--accent-soft); color: var(--accent); font-size: 12px; margin-bottom: 10px; }
.titleBlock h1.mono { font-size: 22px; }
.titleBlock p { text-transform: uppercase; font-size: 12px; letter-spacing: .04em; }
.pageActions { display: flex; gap: 8px; }

.editor { padding: 24px 28px; max-width: 820px; }
.locked { background: var(--st-wait-bg); color: var(--st-wait-fg); padding: .6rem .8rem; border-radius: var(--radius); margin: 0 0 16px; }
.grid { display: grid; grid-template-columns: max-content 1fr; gap: 14px 24px; align-items: start; margin-bottom: 24px; }
label { color: var(--muted); font-size: 13px; padding-top: 7px; }
input, textarea { width: 100%; font-family: var(--mono); font-size: 13px; }
.opchips { display: flex; flex-wrap: wrap; gap: 8px; padding-top: 2px; }
.opchip { border: 1px solid var(--line-2); background: var(--panel); color: var(--text-2); border-radius: var(--radius); padding: 4px 12px; font-size: 13px; }
.opchip:hover:not(:disabled):not(.on) { background: var(--hover); }
.opchip.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.opchip:disabled { cursor: default; opacity: .7; }
.footer { display: flex; align-items: center; gap: 16px; }
.ok { color: var(--accent); }
</style>
