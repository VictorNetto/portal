<script setup>
// Report page (SPEC §6, §7). /reports/new is a small "create" card; once created
// the user lands on /reports/:id where the report is edited under the write lock
// (§3): read-only until "Editar" takes the lock, and the lock is kept alive by a
// heartbeat while the page is open.
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import {
  getReport, createReport, updateReport, deleteReport, listUsers,
  acquireReportLock, heartbeatReport, releaseReportLock, releaseReportLockOnExit, forceReleaseReport,
  addReportSection, updateReportSection, deleteReportSection, reorderReportSections,
  dispatchReport, listReportAttachments, uploadReportAttachment, deleteAttachment,
  fetchAttachmentBlob, downloadAuthed, ApiError,
} from '../api'
import { attachmentPath } from '../markdown'
import { t } from '../i18n'
import { vField } from '../directives'
import { fmtDateTime, fmtTime, fmtDate, fmtPlainDate } from '../dates'
import { useAuthStore } from '../stores/auth'
import AppShell from '../components/AppShell.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import AttachmentsPanel from '../components/AttachmentsPanel.vue'
import OperatorPicker from '../components/OperatorPicker.vue'
import { canCreate, canWriteRecord, canDeleteRecord } from '../access'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Reports use the indigo accent. Set on mount (not in setup): the previous page's
// deferred unmount cleanup would otherwise wipe the attribute right after.
onMounted(() => document.documentElement.setAttribute('data-entity', 'reports'))
onBeforeUnmount(() => document.documentElement.removeAttribute('data-entity'))

const isNew = computed(() => route.name === 'report-new')
const id = computed(() => route.params.id)
const isAdmin = computed(() => auth.user?.role === 'admin')
// May this user change THIS report? (new reports: may they create at all)
const isWriter = computed(() => (isNew.value ? canCreate(auth.user) : canWriteRecord(auth.user, report.value)))
const mayDelete = computed(() => !!report.value && canDeleteRecord(auth.user, report.value))

const report = ref(null)
const loading = ref(!isNew.value)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const allUsers = ref([])
const selectedOps = ref(new Set())
const selectedViewers = ref(new Set())
// The picker needs a name for everyone on the record, even for users that cannot list all accounts.
const knownUsers = computed(() => {
  const byId = new Map(allUsers.value.map((u) => [u.id, u]))
  for (const u of [...(report.value?.operators || []), ...(report.value?.viewers || [])]) if (!byId.has(u.id)) byId.set(u.id, u)
  return [...byId.values()]
})

const blankForm = () => ({
  name: '', client_name: '', start_date: '', end_date: '',
  test_type: '', demand_origin: '', environment: '', test_model: '', scope: '',
  executive_summary_md: '', introduction_md: '', internal_notes: '',
})
const form = ref(blankForm())
const sections = ref([]) // { key, id|null, title, content_markdown }
let keySeed = 0
const newKey = () => `s${++keySeed}`

// --- Lock-driven modes ------------------------------------------------------
const status = computed(() => report.value?.status)
const lock = computed(() => report.value?.lock || null)
const lockMine = computed(() => !!lock.value?.mine)
const lockOther = computed(() => !!lock.value && !lock.value.mine)
// Everything editable: a draft whose lock I hold.
const editing = computed(() => (isNew.value && isWriter.value) || (status.value === 'draft' && lockMine.value && isWriter.value))
// A dispatched report still takes internal notes.
const notesOnly = computed(() => status.value === 'dispatched' && isWriter.value)
const canEditNotes = computed(() => editing.value || notesOnly.value)
const canTakeLock = computed(() => status.value === 'draft' && !lock.value && isWriter.value)

// --- Load -------------------------------------------------------------------
function sync() {
  const r = report.value
  const f = blankForm()
  for (const k of Object.keys(f)) f[k] = r[k] ?? ''
  form.value = f
  selectedOps.value = new Set((r.operators || []).map((o) => o.id))
  selectedViewers.value = new Set((r.viewers || []).map((o) => o.id))
  sections.value = (r.sections || []).map((s) => ({
    key: newKey(), id: s.id, title: s.title, content_markdown: s.content_markdown || '',
  }))
  snapshot.value = snapshotOf()
}

const snapshot = ref('')
const snapshotOf = () => JSON.stringify({ f: form.value, o: [...selectedOps.value].sort(), v: [...selectedViewers.value].sort(), s: sections.value })
const dirty = computed(() => !!report.value && snapshot.value !== snapshotOf())

async function load() {
  try { allUsers.value = await listUsers() } catch { /* non-fatal */ }
  if (isNew.value && !isWriter.value) { router.replace('/hub?entity=reports'); return }
  if (isNew.value) { selectedOps.value = new Set(auth.user?.id ? [auth.user.id] : []); selectedViewers.value = new Set(); loading.value = false; return }
  loading.value = true; error.value = ''
  try { report.value = await getReport(id.value); sync(); await loadEvidence() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

// --- Creating ---------------------------------------------------------------
const created = ref({ name: '', client_name: '', start_date: '', end_date: '' })
async function create() {
  saving.value = true; error.value = ''
  try {
    const r = await createReport({
      name: created.value.name,
      client_name: created.value.client_name || null,
      start_date: created.value.start_date || null,
      end_date: created.value.end_date || null,
      operator_ids: [...selectedOps.value],
      viewer_ids: [...selectedViewers.value],
    })
    report.value = r
    sync()  // this component instance is reused for /reports/:id, so fill the editor now
    await router.replace(`/reports/${r.id}`)
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.create') }
  finally { saving.value = false }
}

// --- Saving -----------------------------------------------------------------
const nullIfBlank = (v) => (String(v ?? '').trim() === '' ? null : v)

async function save() {
  saving.value = true; error.value = ''; notice.value = ''
  try {
    let r
    if (editing.value) {
      r = await updateReport(id.value, {
        name: form.value.name,
        client_name: nullIfBlank(form.value.client_name),
        start_date: nullIfBlank(form.value.start_date),
        end_date: nullIfBlank(form.value.end_date),
        test_type: nullIfBlank(form.value.test_type),
        demand_origin: nullIfBlank(form.value.demand_origin),
        environment: nullIfBlank(form.value.environment),
        test_model: nullIfBlank(form.value.test_model),
        scope: nullIfBlank(form.value.scope),
        executive_summary_md: nullIfBlank(form.value.executive_summary_md),
        introduction_md: nullIfBlank(form.value.introduction_md),
        internal_notes: nullIfBlank(form.value.internal_notes),
        operator_ids: [...selectedOps.value],
        viewer_ids: [...selectedViewers.value],
      })
      r = await saveSections(r)
    } else {
      r = await updateReport(id.value, {
        internal_notes: nullIfBlank(form.value.internal_notes),
        viewer_ids: [...selectedViewers.value],
      })
    }
    report.value = r
    sync()
    notice.value = t('rpt.saved')
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : t('errors.save')
    if (e instanceof ApiError && e.status === 409) await reloadKeepingForm()
  } finally { saving.value = false }
}

// Reconcile the local section list with the server: delete removed ones, add new
// ones, update changed ones, then fix the order.
async function saveSections(r) {
  const keep = new Set(sections.value.filter((s) => s.id).map((s) => s.id))
  for (const s of r.sections) if (!keep.has(s.id)) r = await deleteReportSection(id.value, s.id)
  for (const s of sections.value.filter((x) => !x.id)) {
    r = await addReportSection(id.value, { title: s.title, content_markdown: nullIfBlank(s.content_markdown) })
    s.id = r.sections[r.sections.length - 1].id
  }
  const byId = Object.fromEntries(r.sections.map((s) => [s.id, s]))
  for (const s of sections.value) {
    const srv = byId[s.id]
    if (srv && (srv.title !== s.title || (srv.content_markdown || '') !== s.content_markdown)) {
      r = await updateReportSection(id.value, s.id, { title: s.title, content_markdown: nullIfBlank(s.content_markdown) })
    }
  }
  const desired = sections.value.map((s) => s.id)
  if (JSON.stringify(desired) !== JSON.stringify(r.sections.map((s) => s.id))) {
    r = await reorderReportSections(id.value, desired)
  }
  return r
}

async function reloadKeepingForm() {
  try { report.value = await getReport(id.value) } catch { /* ignore */ }
}

// --- Sections UI -----------------------------------------------------------
function addSection() { sections.value.push({ key: newKey(), id: null, title: '', content_markdown: '' }) }
function removeSection(i) { sections.value.splice(i, 1) }
function moveSection(i, d) {
  const j = i + d
  if (j < 0 || j >= sections.value.length) return
  const next = [...sections.value]
  ;[next[i], next[j]] = [next[j], next[i]]
  sections.value = next
}

// --- Lock -----------------------------------------------------------------
async function takeLock() {
  error.value = ''
  try { report.value = await acquireReportLock(id.value); notice.value = '' }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update'); await reloadKeepingForm() }
}
async function giveUpLock() {
  if (dirty.value && !confirm(t('rpt.discardChanges'))) return
  try { await releaseReportLock(id.value) } catch { /* ignore */ }
  await load()
}
async function forceRelease() {
  if (!confirm(t('rpt.confirmForce', { user: lock.value?.holder_username }))) return
  try { await forceReleaseReport(id.value); await reloadKeepingForm() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update') }
}

// Keep the lock alive while the editor is open. A 409 means it was lost
// (expired, or an admin released it): fall back to read-only.
let beat = null
function startBeat() {
  stopBeat()
  beat = setInterval(async () => {
    if (!lockMine.value || document.hidden) return
    try { report.value = await heartbeatReport(id.value) }
    catch { await reloadKeepingForm(); error.value = t('rpt.lockLost') }
  }, 60_000)
}
function stopBeat() { if (beat) { clearInterval(beat); beat = null } }
watch(lockMine, (mine) => (mine ? startBeat() : stopBeat()), { immediate: true })

// Free the lock when leaving, unless the destination is one of this report's own
// vulnerability editors (the operator is still working on it).
const KEEP_LOCK_ROUTES = ['vuln-detail', 'report-vuln-new']
const warnUnload = (e) => { if (editing.value && dirty.value) { e.preventDefault(); e.returnValue = '' } }
onMounted(() => window.addEventListener('beforeunload', warnUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', warnUnload))
onBeforeRouteLeave(async (to) => {
  if (editing.value && dirty.value && !confirm(t('common.unsavedLeave'))) return false
  // Moving from /reports/new to the report just created is not "leaving" it.
  const sameReport = to.name === 'report-detail' && to.params.id === report.value?.id
  if (lockMine.value && !sameReport && !KEEP_LOCK_ROUTES.includes(to.name)) {
    try { await releaseReportLock(report.value.id) } catch { /* ignore */ }
  }
})
const onPageHide = () => { if (lockMine.value) releaseReportLockOnExit(id.value) }
onMounted(() => window.addEventListener('pagehide', onPageHide))
onBeforeUnmount(() => { window.removeEventListener('pagehide', onPageHide); stopBeat() })

// --- Dispatch & export --------------------------------------------------------
const dispatching = ref(false)
const canDispatch = computed(() => (editing.value && status.value === 'draft') || (status.value === 'dispatching' && isWriter.value))

async function doDispatch() {
  const retry = status.value === 'dispatching'
  if (!retry && !confirm(t('rpt.confirmDispatch'))) return
  error.value = ''; notice.value = ''
  if (!retry && dirty.value) { await save(); if (error.value) return }
  dispatching.value = true
  try {
    report.value = await dispatchReport(id.value)
    sync()
    notice.value = t('rpt.dispatchedOk')
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : t('errors.dispatch')
    await reloadKeepingForm()  // shows the new state (e.g. stuck in dispatching)
  } finally { dispatching.value = false }
}

async function exportAs(format) {
  error.value = ''
  try { await downloadAuthed(`/reports/${id.value}/export?format=${format}`, `${report.value.internal_id}.${format}`) }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
}

// --- Evidence bundle (§7): files and images usable in the narrative sections ----
const evidence = ref([])
const evUploading = ref(false)
const evError = ref('')
const ALLOWED_EXT = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'csv', 'zip']
const MAX_BYTES = 50 * 1024 * 1024

async function loadEvidence() {
  try { evidence.value = await listReportAttachments(id.value) } catch { /* non-fatal */ }
}
function evErrorFor(e, name) {
  if (!(e instanceof ApiError)) return t('attach.errGeneric', { name })
  if (e.status === 413) return t('attach.errSize', { name })
  if (e.status === 409) return t('rpt.lockLost')
  if (e.status === 422) return t('attach.errEmpty', { name })
  if (e.status === 415) {
    return /does not match/i.test(e.detail || '') ? t('attach.errMismatch', { name }) : t('attach.errType', { name })
  }
  return t('attach.errGeneric', { name })
}
async function uploadEvidenceOne(file, displayName) {
  const name = file.name || 'file'
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED_EXT.includes(ext)) { evError.value = t('attach.errType', { name }); return null }
  if (file.size > MAX_BYTES) { evError.value = t('attach.errSize', { name }); return null }
  try {
    const att = await uploadReportAttachment(id.value, file, displayName)
    evidence.value = [...evidence.value, att]
    return att
  } catch (e) { evError.value = evErrorFor(e, name); return null }
}
async function onEvidenceUpload(files) {
  evError.value = ''; evUploading.value = true
  try { for (const f of files) await uploadEvidenceOne(f, null) } finally { evUploading.value = false }
}
// Pasted / dropped / picked images in the narrative editors land in the evidence bundle.
async function uploadEditorImage(file) {
  evError.value = ''
  const base = (file.name || 'imagem').replace(/\.[^.]+$/, '')
  const name = prompt(t('md.imageName'), base)
  if (name === null) return null
  const att = await uploadEvidenceOne(file, name.trim() || base)
  return att ? { id: att.id, name: att.display_name || base } : null
}
async function removeEvidence(a) {
  if (!confirm(t('attach.confirmRemove', { name: a.display_name || a.original_filename }))) return
  try {
    await deleteAttachment(a.id)
    evidence.value = evidence.value.filter((x) => x.id !== a.id)
  } catch (e) { evError.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}
async function downloadEvidence(a) {
  try {
    const url = URL.createObjectURL(await fetchAttachmentBlob(a.id))
    const link = document.createElement('a')
    link.href = url; link.download = a.original_filename; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch { evError.value = t('errors.load') }
}
async function copyEvidenceMarkdown(a) {
  const md = `![${a.display_name || a.original_filename}](${attachmentPath(a.id)})`
  try { await navigator.clipboard.writeText(md) } catch { /* clipboard unavailable */ }
}

// --- Vulnerabilities in the report --------------------------------------------
async function openVuln(v) {
  if (dirty.value && editing.value) await save()
  router.push(`/vulnerabilities/${v.id}`)
}
async function addVuln() {
  if (dirty.value) await save()
  if (error.value) return
  router.push(`/reports/${id.value}/vulnerabilities/new`)
}
const sevClass = (s) => (Number(s) >= 7 ? 'hi' : Number(s) >= 4 ? 'me' : 'lo')
const opNames = (v) => (v.operators?.length ? v.operators.map((o) => o.username).join(', ') : '—')

async function remove() {
  if (!confirm(t('reports.confirmDelete'))) return
  try { await deleteReport(id.value); router.push('/hub?entity=reports') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

onMounted(load)
watch(() => route.fullPath, () => { if (!isNew.value && report.value?.id !== id.value) load() })
</script>

<template>
  <AppShell>
    <nav class="crumbs">
      <a @click="router.push('/hub')">{{ t('vform.breadcrumbRoot') }}</a>
      <span>›</span>
      <a @click="router.push('/hub?entity=reports')">{{ t('hub.tabReports') }}</a>
      <span>›</span>
      <strong>{{ isNew ? t('rpt.newTitle') : (report?.internal_id || '…') }}</strong>
    </nav>

    <!-- ===== Create card ===== -->
    <template v-if="isNew">
      <div class="pageTop">
        <div class="titleBlock">
          <h1>{{ t('rpt.newTitle') }}</h1>
          <p>{{ t('rpt.newHint') }}</p>
        </div>
      </div>
      <p v-if="error" class="err msg">{{ error }}</p>
      <section class="panel card createCard">
        <div class="f">
          <label>{{ t('rpt.name') }} *</label>
          <input v-field v-model="created.name" :placeholder="t('rpt.namePh')" maxlength="200" />
        </div>
        <div class="f">
          <label>{{ t('rpt.client') }}</label>
          <input v-field v-model="created.client_name" maxlength="200" />
        </div>
        <div class="twoCol">
          <div class="f"><label>{{ t('rpt.start') }}</label><input v-model="created.start_date" type="date" /></div>
          <div class="f"><label>{{ t('rpt.end') }}</label><input v-model="created.end_date" type="date" /></div>
        </div>
        <div class="f">
          <label>{{ t('vform.operators') }}</label>
          <OperatorPicker v-model="selectedOps" :users="knownUsers" />
        </div>
        <div class="f">
          <label>{{ t('vform.sharedWith') }}</label>
          <OperatorPicker v-model="selectedViewers" :users="knownUsers" :show-self="false" />
        </div>
        <div class="createActions">
          <button class="btn" @click="router.push('/hub?entity=reports')">{{ t('vform.cancel') }}</button>
          <button class="btn primary" :disabled="saving || !created.name.trim()" @click="create">
            {{ t('rpt.create') }}
          </button>
        </div>
      </section>
    </template>

    <!-- ===== Editor ===== -->
    <template v-else>
      <div class="pageTop">
        <div class="titleBlock">
          <h1>{{ report?.name || '…' }}</h1>
          <p v-if="report" class="subline">
            <span class="pill" :class="'s-' + report.status">{{ t('status.' + report.status) }}</span>
            <span class="mono">{{ report.internal_id }}</span>
            <span>{{ t('cols.updatedAt') }} {{ fmtDateTime(report.updated_at) }}</span>
          </p>
        </div>
        <div class="pageActions" v-if="report">
          <button v-if="status === 'draft' && mayDelete" class="btn danger" @click="remove">{{ t('rowActions.delete') }}</button>
          <button class="btn" @click="router.push('/hub?entity=reports')">{{ t('rpt.back') }}</button>
          <button class="btn" @click="exportAs('pdf')">{{ t('rpt.exportPdf') }}</button>
          <button class="btn" @click="exportAs('xlsx')">{{ t('rpt.exportXlsx') }}</button>
          <button class="btn" @click="exportAs('docx')">{{ t('rpt.exportDocx') }}</button>
          <button v-if="canTakeLock" class="btn primary" @click="takeLock">{{ t('rpt.edit') }}</button>
          <button v-if="lockMine && status === 'draft'" class="btn" @click="giveUpLock">{{ t('rpt.stopEditing') }}</button>
          <button v-if="editing || notesOnly" class="btn" :class="{ primary: !canDispatch }" :disabled="saving" @click="save">
            {{ saving ? t('vuln.saving') : t('vuln.save') }}
          </button>
          <button v-if="canDispatch" class="btn primary" :disabled="dispatching || saving" @click="doDispatch">
            {{ dispatching ? t('rpt.dispatchingBtn') : (status === 'dispatching' ? t('rpt.retry') : t('actions.dispatch')) }}
          </button>
        </div>
      </div>

      <p v-if="notice" class="ok msg">{{ notice }}</p>
      <p v-if="error" class="err msg">{{ error }}</p>
      <p v-if="loading" class="muted">{{ t('vuln.loading') }}</p>

      <template v-else-if="report">
        <!-- lock banner -->
        <p v-if="status === 'draft' && lockMine" class="banner mine">
          {{ t('rpt.youAreEditing', { time: fmtTime(lock.expires_at) }) }}
        </p>
        <p v-else-if="status === 'draft' && lockOther" class="banner other">
          {{ t('rpt.lockedBy', { user: lock.holder_username, time: fmtTime(lock.acquired_at) }) }}
          <button v-if="isAdmin" class="link" @click="forceRelease">{{ t('rpt.forceRelease') }}</button>
        </p>
        <p v-else-if="status === 'dispatching' && report.dispatch_error" class="banner other">{{ report.dispatch_error }}</p>

        <!-- General -->
        <section class="panel card">
          <h2 class="secTitle">{{ t('rpt.general') }}</h2>
          <div class="grid4">
            <div class="f wide2">
              <label>{{ t('rpt.name') }} *</label>
              <input v-field v-model="form.name" :disabled="!editing" maxlength="200" />
            </div>
            <div class="f wide2">
              <label>{{ t('rpt.client') }}</label>
              <input v-field v-model="form.client_name" :disabled="!editing" maxlength="200" />
            </div>
            <div class="f"><label>{{ t('rpt.start') }}</label><input v-model="form.start_date" type="date" :disabled="!editing" /></div>
            <div class="f"><label>{{ t('rpt.end') }}</label><input v-model="form.end_date" type="date" :disabled="!editing" /></div>
            <div class="f wide2">
              <label>{{ t('vform.operators') }}</label>
              <OperatorPicker v-model="selectedOps" :users="knownUsers" :disabled="!editing" />
            </div>
            <div v-if="editing || notesOnly || selectedViewers.size" class="f wide2">
              <label>{{ t('vform.sharedWith') }}</label>
              <OperatorPicker v-model="selectedViewers" :users="knownUsers" :show-self="false"
                              :disabled="!(editing || notesOnly)" />
            </div>
          </div>
        </section>

        <!-- Report data -->
        <section class="panel card">
          <h2 class="secTitle">{{ t('rpt.data') }}</h2>
          <div class="grid4">
            <div class="f"><label>{{ t('rpt.testType') }}</label><input v-field v-model="form.test_type" :disabled="!editing" placeholder="infra, web, mobile, API" /></div>
            <div class="f"><label>{{ t('rpt.testModel') }}</label><input v-field v-model="form.test_model" :disabled="!editing" placeholder="graybox, blackbox, whitebox" /></div>
            <div class="f"><label>{{ t('rpt.environment') }}</label><input v-field v-model="form.environment" :disabled="!editing" placeholder="production, staging" /></div>
            <div class="f"><label>{{ t('rpt.origin') }}</label><input v-field v-model="form.demand_origin" :disabled="!editing" /></div>
            <div class="f full">
              <label>{{ t('rpt.scope') }}</label>
              <textarea v-model="form.scope" rows="3" :disabled="!editing" maxlength="5000"></textarea>
            </div>
          </div>
        </section>

        <section class="panel card">
          <h2 class="secTitle">{{ t('rpt.summary') }}</h2>
          <MarkdownEditor v-model="form.executive_summary_md" :disabled="!editing"
                          :image-uploader="editing ? uploadEditorImage : null" />
        </section>

        <section class="panel card">
          <h2 class="secTitle">{{ t('rpt.intro') }}</h2>
          <MarkdownEditor v-model="form.introduction_md" :disabled="!editing"
                          :image-uploader="editing ? uploadEditorImage : null" />
        </section>

        <!-- Free-form sections -->
        <section class="panel card">
          <h2 class="secTitle">{{ t('rpt.extras') }}</h2>
          <p class="hint">{{ t('rpt.extrasHint') }}</p>
          <p v-if="!sections.length" class="muted small">{{ t('rpt.noExtras') }}</p>
          <div v-for="(s, i) in sections" :key="s.key" class="extra">
            <div class="extraHead">
              <input v-model="s.title" :disabled="!editing" :placeholder="t('rpt.sectionTitle')" maxlength="200" />
              <div v-if="editing" class="extraActs">
                <button class="link" :disabled="i === 0" @click="moveSection(i, -1)">{{ t('rpt.up') }}</button>
                <button class="link" :disabled="i === sections.length - 1" @click="moveSection(i, 1)">{{ t('rpt.down') }}</button>
                <button class="link danger" @click="removeSection(i)">{{ t('vform.removeRef') }}</button>
              </div>
            </div>
            <MarkdownEditor v-model="s.content_markdown" :disabled="!editing"
                            :image-uploader="editing ? uploadEditorImage : null" />
          </div>
          <button v-if="editing" class="link addRef" @click="addSection">{{ t('rpt.addSection') }}</button>
        </section>

        <!-- Vulnerabilities -->
        <section class="panel card">
          <div class="secRow">
            <h2 class="secTitle">{{ t('rpt.vulns') }} ({{ report.vulnerabilities.length }})</h2>
            <button v-if="editing" class="btn" @click="addVuln">{{ t('rpt.addVuln') }}</button>
          </div>
          <p v-if="!report.vulnerabilities.length" class="muted small">{{ t('rpt.noVulns') }}</p>
          <table v-else class="vt">
            <thead>
              <tr><th>{{ t('cols.identifier') }}</th><th>{{ t('cols.status') }}</th><th>{{ t('cols.cvss') }}</th><th>{{ t('cols.operators') }}</th><th>{{ t('cols.updatedAt') }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="v in report.vulnerabilities" :key="v.id" @click="openVuln(v)">
                <td class="idcell">{{ v.identifier || '—' }}</td>
                <td><span class="pill" :class="'s-' + v.status">{{ t('status.' + v.status) }}</span></td>
                <td><span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ v.cvss_score }}</span><span v-else>—</span></td>
                <td>{{ opNames(v) }}</td>
                <td class="muted">{{ fmtDate(v.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="panel card">
          <h2 class="secTitle">{{ t('rpt.evidence') }}</h2>
          <p class="hint">{{ t('rpt.evidenceHint') }}</p>
          <AttachmentsPanel :attachments="evidence" :disabled="!editing" :uploading="evUploading" :error="evError"
                            @upload="onEvidenceUpload" @remove="removeEvidence"
                            @download="downloadEvidence" @copy-markdown="copyEvidenceMarkdown" />
        </section>

        <section class="panel card">
          <h2 class="secTitle">{{ t('vform.notes') }}</h2>
          <p class="hint">{{ t('vform.notesHint') }}</p>
          <MarkdownEditor v-model="form.internal_notes" :disabled="!canEditNotes" />
        </section>
      </template>
    </template>
  </AppShell>
</template>

<style scoped>
.crumbs { display: flex; gap: 10px; align-items: center; color: var(--muted); font-size: 13px; margin-bottom: 14px; }
.crumbs a { cursor: pointer; }
.crumbs a:hover { color: var(--text); }
.crumbs strong { color: var(--accent); font-weight: 400; }

.subline { display: flex; align-items: center; gap: 12px; }
.pageActions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.msg { margin: 0 0 14px; font-size: 13px; }
.ok { color: var(--accent); }

.banner { margin: 0 0 16px; padding: 9px 14px; border-radius: var(--radius); font-size: 13px; }
.banner.mine { background: var(--accent-soft); color: var(--accent); }
.banner.other { background: var(--st-wait-bg); color: var(--st-wait-fg); }
.banner.free { background: var(--panel-2); color: var(--muted); border: 1px solid var(--line); }
.banner .link { margin-left: 12px; }

.card { padding: 16px 18px 18px; margin-bottom: 16px; overflow: visible; }
.secTitle { margin: 0 0 12px; font-size: 14px; font-weight: 400; color: var(--text); }
.secRow { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.hint { margin: -6px 0 12px; color: var(--muted); font-size: 12px; }
.small { font-size: 13px; }

.f { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.f label { font-size: 12px; color: var(--muted); }
.f input, .f textarea { width: 100%; }
.grid4 { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px 24px; align-items: start; }
.wide2 { grid-column: span 2; }
.full { grid-column: 1 / -1; }
.twoCol { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.createCard { max-width: 640px; display: grid; gap: 16px; }
.createActions { display: flex; gap: 8px; justify-content: flex-end; }


.extra { margin-bottom: 18px; }
.extraHead { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; }
.extraHead input { flex: 1; }
.extraActs { display: flex; flex: 0 0 auto; }
.extraActs .link { margin-left: 14px; }
.extraActs .link:disabled { opacity: .35; cursor: default; text-decoration: none; }
.addRef { margin: 4px 0 0; }

.vt td { cursor: pointer; }
.vt .idcell { font-family: var(--mono); }

@media (max-width: 1100px) { .grid4 { grid-template-columns: 1fr 1fr; } }
</style>
