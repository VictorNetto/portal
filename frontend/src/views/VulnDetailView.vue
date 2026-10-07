<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import {
  getVuln, createVuln, updateVuln, sendVuln, dispatchVuln, deleteVuln, listUsers,
  listAttachments, uploadAttachment, deleteAttachment, fetchAttachmentBlob,
  transitionVuln, correctVuln, getReport, createReportVuln, acquireReportLock,
  heartbeatReport, releaseReportLock, downloadAuthed, ApiError,
} from '../api'
import { attachmentPath } from '../markdown'
import { fmtTime } from '../dates'
import { t } from '../i18n'
import { vField } from '../directives'
import { useAuthStore } from '../stores/auth'
import AppShell from '../components/AppShell.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import CvssInput from '../components/CvssInput.vue'
import MultiValueInput from '../components/MultiValueInput.vue'
import AttachmentsPanel from '../components/AttachmentsPanel.vue'
import VulnTimeline from '../components/VulnTimeline.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')
const isWriter = computed(() => ['admin', 'writer_all'].includes(auth.user?.role))
const isNew = computed(() => ['vuln-new', 'report-vuln-new'].includes(route.name))

// This is always a vulnerability view -> green accent.
document.documentElement.setAttribute('data-entity', 'vulns')
onUnmounted(() => document.documentElement.removeAttribute('data-entity'))

// `id` is reactive: creating a vuln then router.replace()ing to its detail
// reuses this component, so we react to route changes rather than only mount.
const id = computed(() => route.params.id)

const blankForm = () => ({
  identifier: '', cwe: '', cvss_score: null, cvss_vector: '', source: '',
  description: '', finding_detail: '', mitigation: '', internal_notes: '',
  references: [''],
})

const vuln = ref(null)

// A vuln inside a draft report is edited under that report's lock (SPEC §3): it is
// read-only unless this user holds the lock, and it is saved through the report.
const reportCtx = ref(null)
const reportId = computed(() =>
  route.params.rid || (vuln.value && vuln.value.status === 'draft' ? vuln.value.report_id : null) || null)
const inReport = computed(() => !!reportId.value)
const rLock = computed(() => reportCtx.value?.lock || null)
const lockMine = computed(() => !!rLock.value?.mine)
const lockOther = computed(() => !!rLock.value && !rLock.value.mine)
const form = ref(blankForm())
const loading = ref(!isNew.value)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const showErrors = ref(false) // validation messages appear after a submit attempt

// Operators
const allUsers = ref([])
const selectedOps = ref(new Set()) // user ids

// Attachments
const attachments = ref([])
const uploading = ref(false)
const attachError = ref('')

// --- Field-lock rules (SPEC §4), mirrored for UX; the server enforces anyway.
const ALL_FIELDS = ['identifier', 'cwe', 'description', 'finding_detail', 'mitigation',
  'references', 'cvss_score', 'cvss_vector', 'source', 'internal_notes', 'operators']
const editableFields = computed(() => {
  if (inReport.value) {
    return reportCtx.value?.status === 'draft' && lockMine.value ? new Set(ALL_FIELDS) : new Set()
  }
  if (isNew.value) return new Set(ALL_FIELDS)
  const s = vuln.value?.status
  if (s === 'draft' || s === 'saved_local') return new Set(ALL_FIELDS)
  if (s === 'dispatching') return new Set()
  return new Set(['internal_notes', 'operators'])
})
const canEdit = (f) => editableFields.value.has(f)
const isDraft = computed(() => !inReport.value && (isNew.value || vuln.value?.status === 'draft'))
const isSavedLocal = computed(() => vuln.value?.status === 'saved_local')
const attachEditable = computed(() =>
  inReport.value ? lockMine.value : (isNew.value || ['draft', 'saved_local'].includes(vuln.value?.status)))

// --- Validation -----------------------------------------------------------
const REQUIRED = ['identifier', 'description', 'finding_detail', 'mitigation']
const URL_RE = /^https?:\/\/\S+$/i
const blank = (v) => !String(v ?? '').trim()
const missing = computed(() => REQUIRED.filter((f) => blank(form.value[f])))
const refInvalid = (r) => !!r.trim() && !URL_RE.test(r.trim())
const hasRefErrors = computed(() => form.value.references.some(refInvalid))
const fieldError = (f) => showErrors.value && missing.value.includes(f)

// --- Load / sync ----------------------------------------------------------
// Unsaved-changes tracking: a snapshot of what the form held when last loaded/saved.
const snapshot = ref('')
const currentState = () => JSON.stringify({ f: form.value, o: [...selectedOps.value].sort() })
const dirty = computed(() => !loading.value && snapshot.value !== '' && snapshot.value !== currentState())
const markClean = () => { snapshot.value = currentState() }

function syncForm() {
  const v = vuln.value
  const f = blankForm()
  for (const k of Object.keys(f)) {
    if (k === 'references') f.references = v.references?.length ? [...v.references] : ['']
    else if (k === 'cvss_score') f.cvss_score = v.cvss_score == null ? null : Number(v.cvss_score)
    else f[k] = v[k] ?? ''
  }
  form.value = f
  selectedOps.value = new Set((v.operators || []).map((o) => o.id))
  markClean()
}

function resetForNew() {
  vuln.value = null
  form.value = blankForm()
  selectedOps.value = new Set()
  attachments.value = []
  error.value = notice.value = attachError.value = ''
  showErrors.value = false
  loading.value = false
  markClean()
}

async function loadReportCtx() {
  if (!reportId.value) { reportCtx.value = null; return }
  try { reportCtx.value = await getReport(reportId.value) } catch { reportCtx.value = null }
}

async function loadAttachments() {
  if (!vuln.value) { attachments.value = []; return }
  try { attachments.value = await listAttachments(vuln.value.id) } catch { /* non-fatal */ }
}

async function load() {
  // users for the operator picker, regardless of new/edit
  try { allUsers.value = await listUsers() } catch { /* non-fatal */ }
  if (isNew.value) { resetForNew(); await loadReportCtx(); return }
  // Don't flash the loading state when we just created this very record.
  if (vuln.value?.id !== id.value) loading.value = true
  error.value = ''
  try {
    vuln.value = await getVuln(id.value)
    syncForm()
    await loadAttachments()
    await loadReportCtx()
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

function toggleOp(uid) {
  if (!canEdit('operators')) return
  if (selectedOps.value.has(uid)) selectedOps.value.delete(uid)
  else selectedOps.value.add(uid)
  selectedOps.value = new Set(selectedOps.value)
}

// CWE is always shown as CWE-<digits> (up to 6), as in the prototype.
function onCwe(e) {
  const digits = e.target.value.replace(/\D/g, '').slice(0, 6)
  form.value.cwe = digits ? `CWE-${digits}` : ''
  e.target.value = form.value.cwe
}

// --- References -----------------------------------------------------------
function addRef() { form.value.references.push('') }
function removeRef(i) {
  form.value.references.splice(i, 1)
  if (!form.value.references.length) form.value.references.push('')
}

// --- Persisting -----------------------------------------------------------
function bodyFromForm(fields) {
  const body = {}
  for (const f of fields) {
    if (f === 'operators') continue // sent separately as operator_ids
    const val = form.value[f]
    if (f === 'references') body.references = val.map((r) => r.trim()).filter(Boolean)
    else if (f === 'cvss_score') body.cvss_score = val === '' || val == null ? null : Number(val)
    else body[f] = String(val).trim() === '' ? null : val
  }
  return body
}

// Creates the draft (new) or updates the record; returns the saved vuln.
async function persist() {
  if (hasRefErrors.value) { showErrors.value = true; throw new Error('refs') }
  if (isNew.value) {
    const body = bodyFromForm(ALL_FIELDS)
    body.operator_ids = [...selectedOps.value]
    const created = inReport.value
      ? await createReportVuln(reportId.value, body)
      : await createVuln(body)
    // Set before navigating so the route change doesn't trigger a reload that
    // would flash the form away or overwrite what the user types meanwhile.
    vuln.value = created
    markClean()  // what was typed is now saved: leaving /new must not warn
    await router.replace(`/vulnerabilities/${created.id}`)
    return created
  }
  const body = { version: vuln.value.version, ...bodyFromForm([...editableFields.value]) }
  if (canEdit('operators')) body.operator_ids = [...selectedOps.value]
  vuln.value = await updateVuln(id.value, body)
  syncForm()
  return vuln.value
}

function reportError(e, fallbackKey) {
  if (e instanceof Error && e.message === 'refs') { error.value = t('vform.errRef'); return }
  error.value = e instanceof ApiError ? e.detail : t(fallbackKey)
}

async function save() {
  saving.value = true; error.value = ''; notice.value = ''
  const wasNew = isNew.value
  try {
    await persist()
    notice.value = wasNew ? t('vform.draftCreated') : t('vuln.saved')
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) { error.value = e.detail; await load() }
    else reportError(e, 'errors.save')
  } finally { saving.value = false }
}

async function doSend() {
  showErrors.value = true
  if (missing.value.length || hasRefErrors.value) { error.value = t('vform.errRequiredToSend'); return }
  saving.value = true; error.value = ''; notice.value = ''
  try {
    const saved = await persist()
    vuln.value = await sendVuln(saved.id)
    syncForm()
    notice.value = t('vuln.sent')
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) { error.value = e.detail; await load() }
    else reportError(e, 'errors.send')
  } finally { saving.value = false }
}

async function doDispatch() {
  if (!confirm(t('vuln.confirmDispatch'))) return
  error.value = ''; notice.value = ''
  try { vuln.value = await dispatchVuln(id.value); syncForm(); notice.value = t('vuln.dispatched') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.dispatch') }
}

// --- Lifecycle after acknowledgment (waiting fix -> retest -> fixed) ---------
const NEXT_ACTIONS = {
  acknowledged: [{ to: 'waiting_fix', label: 'transitions.toWaitingFix' }],
  waiting_fix: [{ to: 'pending_retest', label: 'transitions.toRetest' }],
  pending_retest: [
    { to: 'waiting_fix', label: 'transitions.retestFailed' },
    { to: 'fixed', label: 'transitions.retestPassed', primary: true },
  ],
}
const nextActions = computed(() => (isWriter.value && vuln.value ? NEXT_ACTIONS[vuln.value.status] || [] : []))

async function doTransition(action) {
  error.value = ''; notice.value = ''
  try {
    vuln.value = await transitionVuln(id.value, action.to)
    syncForm()
    notice.value = t('transitions.done', { status: t('status.' + action.to) })
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update'); await load() }
}

// --- Admin correction (D6): move back to an earlier status -------------------
const ORDER = ['saved_local', 'dispatched', 'acknowledged', 'waiting_fix', 'pending_retest', 'fixed']
const correctionTargets = computed(() => {
  const i = ORDER.indexOf(vuln.value?.status)
  return i > 0 ? ORDER.slice(0, i) : []
})
const showCorrection = ref(false)
const corr = ref({ to: '', reason: '' })
function openCorrection() {
  corr.value = { to: correctionTargets.value[correctionTargets.value.length - 1] || '', reason: '' }
  showCorrection.value = !showCorrection.value
}
async function applyCorrection() {
  error.value = ''; notice.value = ''
  try {
    vuln.value = await correctVuln(id.value, corr.value.to, corr.value.reason)
    syncForm()
    showCorrection.value = false
    notice.value = t('correction.done', { status: t('status.' + corr.value.to) })
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update') }
}

async function exportAs(format) {
  error.value = ''
  try { await downloadAuthed(`/vulnerabilities/${id.value}/export?format=${format}`, `vulnerabilidade.${format}`) }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
}

async function remove() {
  if (!confirm(t('vuln.confirmDelete'))) return
  try { await deleteVuln(id.value); router.push(inReport.value ? `/reports/${reportId.value}` : '/hub') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

// --- Attachments ----------------------------------------------------------
const ALLOWED_EXT = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'csv', 'zip']
const MAX_BYTES = 50 * 1024 * 1024

// Attachments need an owner: the first upload (or pasted image) on an unsaved
// form saves it as a draft (spec: save draft -> get id -> upload).
async function ensureDraftId() {
  if (vuln.value) return vuln.value.id
  const created = await persist()
  notice.value = t('vform.draftCreated')
  return created.id
}

function uploadErrorMessage(e, name) {
  if (!(e instanceof ApiError)) return t('attach.errGeneric', { name })
  if (e.status === 413) return t('attach.errSize', { name })
  if (e.status === 409) return t('attach.errLocked')
  if (e.status === 422) return t('attach.errEmpty', { name })
  if (e.status === 415) {
    return /does not match/i.test(e.detail || '')
      ? t('attach.errMismatch', { name }) : t('attach.errType', { name })
  }
  return t('attach.errGeneric', { name })
}

// Uploads one file; returns the attachment, or null after setting attachError.
async function uploadOne(file, displayName) {
  const name = file.name || 'file'
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED_EXT.includes(ext)) { attachError.value = t('attach.errType', { name }); return null }
  if (file.size > MAX_BYTES) { attachError.value = t('attach.errSize', { name }); return null }
  try {
    const vid = await ensureDraftId()
    const att = await uploadAttachment(vid, file, displayName)
    attachments.value = [...attachments.value, att]
    return att
  } catch (e) {
    if (e instanceof Error && e.message === 'refs') { error.value = t('vform.errRef'); return null }
    attachError.value = uploadErrorMessage(e, name)
    return null
  }
}

async function onPanelUpload(files) {
  attachError.value = ''
  uploading.value = true
  try { for (const f of files) await uploadOne(f, null) }
  finally { uploading.value = false }
}

// Used by the markdown editors for pasted / dropped / picked images.
async function uploadEditorImage(file) {
  attachError.value = ''
  const base = (file.name || 'imagem').replace(/\.[^.]+$/, '')
  const name = prompt(t('md.imageName'), base)
  if (name === null) return null
  const att = await uploadOne(file, name.trim() || base)
  return att ? { id: att.id, name: att.display_name || base } : null
}

async function removeAttachment(a) {
  if (!confirm(t('attach.confirmRemove', { name: a.display_name || a.original_filename }))) return
  attachError.value = ''
  try {
    await deleteAttachment(a.id)
    attachments.value = attachments.value.filter((x) => x.id !== a.id)
  } catch (e) { attachError.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

async function downloadAttachment(a) {
  try {
    const url = URL.createObjectURL(await fetchAttachmentBlob(a.id))
    const link = document.createElement('a')
    link.href = url
    link.download = a.original_filename
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch { attachError.value = t('errors.load') }
}

async function copyMarkdown(a) {
  const md = `![${a.display_name || a.original_filename}](${attachmentPath(a.id)})`
  try { await navigator.clipboard.writeText(md) } catch { /* clipboard unavailable */ }
}

// --- Report lock (only relevant for vulns inside a draft report) -------------
async function takeLock() {
  error.value = ''
  try { reportCtx.value = await acquireReportLock(reportId.value) }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update'); await loadReportCtx() }
}
let beat = null
function stopBeat() { if (beat) { clearInterval(beat); beat = null } }
watch(lockMine, (mine) => {
  stopBeat()
  if (!mine) return
  beat = setInterval(async () => {
    if (document.hidden) return
    try { reportCtx.value = await heartbeatReport(reportId.value) }
    catch { await loadReportCtx(); error.value = t('rpt.lockLost') }
  }, 60_000)
}, { immediate: true })
onUnmounted(stopBeat)
// Keep the lock when moving between the report and its own vulnerabilities;
// release it when leaving for anywhere else.
const KEEP_LOCK_ROUTES = ['report-detail', 'vuln-detail', 'report-vuln-new']
const warnUnload = (e) => { if (dirty.value) { e.preventDefault(); e.returnValue = '' } }
onMounted(() => window.addEventListener('beforeunload', warnUnload))
onUnmounted(() => window.removeEventListener('beforeunload', warnUnload))
onBeforeRouteLeave(async (to) => {
  if (dirty.value && !confirm(t('common.unsavedLeave'))) return false
  if (inReport.value && lockMine.value && !KEEP_LOCK_ROUTES.includes(to.name)) {
    try { await releaseReportLock(reportId.value) } catch { /* ignore */ }
  }
})
const leave = () => router.push(inReport.value ? `/reports/${reportId.value}` : '/hub')

onMounted(load)
// Navigating between new <-> a created detail reuses this component.
watch(() => route.fullPath, () => {
  if (isNew.value || vuln.value?.id !== id.value) load()
})
</script>

<template>
  <AppShell>
    <nav class="crumbs">
      <a @click="router.push('/hub')">{{ t('vform.breadcrumbRoot') }}</a>
      <span>›</span>
      <template v-if="inReport">
        <a @click="router.push('/hub?entity=reports')">{{ t('hub.tabReports') }}</a>
        <span>›</span>
        <a @click="leave">{{ reportCtx?.internal_id || '…' }}</a>
        <span>›</span>
      </template>
      <template v-else>
        <a @click="router.push('/hub')">{{ t('vform.breadcrumbSection') }}</a>
        <span>›</span>
      </template>
      <strong>{{ isNew ? t('vform.createTitle') : (vuln?.internal_id || vuln?.identifier || t('vuln.draft')) }}</strong>
    </nav>

    <div class="pageTop">
      <div class="titleBlock">
        <h1 :class="{ mono: !isNew }">
          {{ isNew ? t('vform.createTitle') : (vuln?.internal_id || t('vuln.draft')) }}
        </h1>
        <p v-if="vuln">{{ t('status.' + vuln.status) }} · v{{ vuln.version }}</p>
        <p v-else-if="isNew">{{ t('vform.createHint') }}</p>
      </div>
      <div class="pageActions">
        <button v-if="!isNew" class="btn danger" @click="remove">{{ t('rowActions.delete') }}</button>
        <button v-if="!isNew" class="btn" @click="exportAs('pdf')">{{ t('rpt.exportPdf') }}</button>
        <button v-if="!isNew" class="btn" @click="exportAs('docx')">{{ t('rpt.exportDocx') }}</button>
        <button class="btn" @click="leave">{{ inReport ? t('rpt.back') : t('vform.cancel') }}</button>
        <button v-if="isAdmin && correctionTargets.length" class="btn" @click="openCorrection">
          {{ t('correction.button') }}
        </button>
        <button v-for="a in nextActions" :key="a.to" class="btn" :class="{ primary: a.primary }"
                @click="doTransition(a)">{{ t(a.label) }}</button>
        <button v-if="isSavedLocal" class="btn" @click="doDispatch">{{ t('actions.dispatch') }}</button>
        <button v-if="isDraft" class="btn" :disabled="saving" @click="doSend">{{ t('vform.send') }}</button>
        <button class="btn primary" :disabled="saving || !editableFields.size" @click="save">
          {{ saving ? t('vuln.saving') : (isDraft ? t('vform.saveDraft') : t('vuln.save')) }}
        </button>
      </div>
    </div>

    <section v-if="showCorrection" class="panel card correction">
      <h2 class="secTitle">{{ t('correction.title') }}</h2>
      <p class="hint">{{ t('correction.hint') }}</p>
      <div class="corrRow">
        <div class="f">
          <label>{{ t('correction.target') }}</label>
          <select v-model="corr.to">
            <option v-for="s in correctionTargets" :key="s" :value="s">{{ t('status.' + s) }}</option>
          </select>
        </div>
        <div class="f grow">
          <label>{{ t('correction.reason') }}</label>
          <input v-model="corr.reason" :placeholder="t('correction.reasonPh')" maxlength="500" />
        </div>
        <div class="corrActions">
          <button class="btn" @click="showCorrection = false">{{ t('vform.cancel') }}</button>
          <button class="btn primary" :disabled="corr.reason.trim().length < 5" @click="applyCorrection">
            {{ t('correction.apply') }}
          </button>
        </div>
      </div>
    </section>

    <p v-if="inReport && reportCtx && reportCtx.status === 'draft'" class="banner"
       :class="lockMine ? 'mine' : 'other'">
      <template v-if="lockMine">{{ t('vrep.editing', { report: reportCtx.internal_id, time: fmtTime(rLock.expires_at) }) }}</template>
      <template v-else-if="lockOther">{{ t('vrep.lockedBy', { user: rLock.holder_username, report: reportCtx.internal_id }) }}</template>
      <template v-else>{{ t('vrep.readOnly', { report: reportCtx.internal_id }) }}
        <button v-if="isWriter" class="link" @click="takeLock">{{ t('rpt.edit') }}</button></template>
    </p>

    <p v-if="notice" class="ok msg">{{ notice }}</p>
    <p v-if="error" class="err msg">{{ error }}</p>

    <p v-if="loading" class="muted">{{ t('vuln.loading') }}</p>
    <template v-else>
      <p v-if="!editableFields.size" class="locked">
        {{ t('vuln.locked', { status: t('status.' + (vuln?.status || 'dispatching')) }) }}
      </p>

      <section v-if="vuln && !inReport" class="panel card">
        <h2 class="secTitle">{{ t('timeline.title') }}</h2>
        <VulnTimeline :vuln="vuln" />
      </section>

      <section class="panel card">
        <h2 class="secTitle">{{ t('vform.general') }}</h2>
        <div class="infoGrid">
          <div class="f">
            <label>{{ t('vform.identifier') }} *</label>
            <input v-field v-model="form.identifier" :class="{ invalid: fieldError('identifier') }"
                   :placeholder="t('vform.identifierPh')" :disabled="!canEdit('identifier')" />
            <small v-if="fieldError('identifier')" class="fieldErr">{{ t('vform.required') }}</small>
          </div>
          <div class="f">
            <label>{{ t('vform.cwe') }}</label>
            <input v-field :value="form.cwe" inputmode="numeric" autocomplete="off" placeholder="CWE-79"
                   :disabled="!canEdit('cwe')" @input="onCwe" @blur="onCwe" />
          </div>
          <div class="f">
            <label>{{ t('vform.cvss') }}</label>
            <CvssInput v-model="form.cvss_score" :disabled="!canEdit('cvss_score')" />
          </div>
          <div class="f">
            <label>{{ t('vform.cvssVector') }}</label>
            <input v-field v-model="form.cvss_vector" placeholder="CVSS:3.1/AV:N/AC:L/…"
                   :disabled="!canEdit('cvss_vector')" />
          </div>

          <div class="row2">
            <div class="f">
              <label>{{ t('vform.sources') }}</label>
              <MultiValueInput v-model="form.source" :placeholder="t('vform.sourcesPh')"
                               :disabled="!canEdit('source')" />
            </div>
            <div class="f">
              <label>{{ t('vform.operators') }}</label>
              <div class="opchips" :class="{ locked: !canEdit('operators') }">
                <button v-for="u in allUsers" :key="u.id" type="button" class="opchip"
                        :class="{ on: selectedOps.has(u.id) }"
                        :disabled="!canEdit('operators')" @click="toggleOp(u.id)">
                  {{ u.username }}
                </button>
                <span v-if="!allUsers.length" class="muted">{{ t('vform.noOperators') }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div class="layout">
        <div class="stack">
          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.description') }} *</h2>
            <MarkdownEditor v-model="form.description" :disabled="!canEdit('description')"
                            :invalid="fieldError('description')"
                            :image-uploader="attachEditable ? uploadEditorImage : null" />
            <small v-if="fieldError('description')" class="fieldErr">{{ t('vform.required') }}</small>
          </section>

          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.finding') }} *</h2>
            <MarkdownEditor v-model="form.finding_detail" :disabled="!canEdit('finding_detail')"
                            :invalid="fieldError('finding_detail')"
                            :image-uploader="attachEditable ? uploadEditorImage : null" />
            <small v-if="fieldError('finding_detail')" class="fieldErr">{{ t('vform.required') }}</small>
          </section>

          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.mitigation') }} *</h2>
            <MarkdownEditor v-model="form.mitigation" :disabled="!canEdit('mitigation')"
                            :invalid="fieldError('mitigation')"
                            :image-uploader="attachEditable ? uploadEditorImage : null" />
            <small v-if="fieldError('mitigation')" class="fieldErr">{{ t('vform.required') }}</small>
          </section>

          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.references') }}</h2>
            <p class="hint">{{ t('vform.referencesHint') }}</p>
            <div class="refs">
              <div v-for="(_, i) in form.references" :key="i" class="refRow">
                <div class="f">
                  <input v-field v-model="form.references[i]" type="url" :placeholder="t('vform.refPh')"
                         :class="{ invalid: showErrors && refInvalid(form.references[i]) }"
                         :disabled="!canEdit('references')" />
                  <small v-if="showErrors && refInvalid(form.references[i])" class="fieldErr">{{ t('vform.errRef') }}</small>
                </div>
                <button v-if="canEdit('references')" type="button" class="btn" @click="removeRef(i)">
                  {{ t('vform.removeRef') }}
                </button>
              </div>
            </div>
            <button v-if="canEdit('references')" type="button" class="link addRef" @click="addRef">
              {{ t('vform.addRef') }}
            </button>
          </section>
        </div>

        <div class="stack">
          <section class="panel card">
            <h2 class="secTitle">{{ t('attach.title') }}</h2>
            <p class="hint">{{ t('attach.hint') }}</p>
            <AttachmentsPanel :attachments="attachments" :disabled="!attachEditable"
                              :uploading="uploading" :error="attachError"
                              @upload="onPanelUpload" @remove="removeAttachment"
                              @download="downloadAttachment" @copy-markdown="copyMarkdown" />
          </section>

          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.notes') }}</h2>
            <p class="hint">{{ t('vform.notesHint') }}</p>
            <MarkdownEditor v-model="form.internal_notes" :disabled="!canEdit('internal_notes')" />
          </section>
        </div>
      </div>
    </template>
  </AppShell>
</template>

<style scoped>
.crumbs { display: flex; gap: 10px; align-items: center; color: var(--muted); font-size: 13px; margin-bottom: 14px; }
.crumbs a { cursor: pointer; }
.crumbs a:hover { color: var(--text); }
.crumbs strong { color: var(--accent); font-weight: 400; }

.titleBlock h1.mono { font-size: 22px; }
.pageActions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }

.msg { margin: 0 0 14px; font-size: 13px; }
.ok { color: var(--accent); }
.locked { background: var(--st-wait-bg); color: var(--st-wait-fg); padding: .6rem .8rem; border-radius: var(--radius); margin: 0 0 16px; }

.card { padding: 16px 18px 18px; margin-bottom: 16px; overflow: visible; }
.secTitle { margin: 0 0 12px; font-size: 14px; font-weight: 400; color: var(--text); }
.hint { margin: -6px 0 12px; color: var(--muted); font-size: 12px; }

.f { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.f label { font-size: 12px; color: var(--muted); }
.f input { width: 100%; }
input.invalid { border-color: var(--danger); }
.fieldErr { color: var(--danger); font-size: 12px; margin-top: 4px; display: block; }

.infoGrid { display: grid; grid-template-columns: 1.3fr .85fr .85fr 1.25fr; gap: 16px 24px; align-items: start; }
.row2 { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1.6fr; gap: 24px; }

.layout { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(340px, .9fr); gap: 16px; align-items: start; }
.stack { min-width: 0; }

.refs { display: grid; gap: 8px; }
.refRow { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: start; }
.addRef { margin: 12px 0 0; }

.banner { margin: 0 0 16px; padding: 9px 14px; border-radius: var(--radius); font-size: 13px; }
.banner.mine { background: var(--accent-soft); color: var(--accent); }
.banner.other { background: var(--st-wait-bg); color: var(--st-wait-fg); }
.banner .link { margin-left: 12px; }
.corrRow { display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap; }
.corrRow .grow { flex: 1 1 280px; }
.corrActions { display: flex; gap: 8px; }
.opchips { display: flex; flex-wrap: wrap; gap: 8px; min-height: 32px; align-items: center; }
.opchip { border: 1px solid var(--line-2); background: var(--panel); color: var(--text-2); border-radius: var(--radius); padding: 4px 12px; font-size: 13px; }
.opchip:hover:not(:disabled):not(.on) { background: var(--hover); }
.opchip.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.opchip:disabled { cursor: default; opacity: .7; }

@media (max-width: 1100px) {
  .infoGrid, .row2, .layout { grid-template-columns: 1fr; }
}
</style>
