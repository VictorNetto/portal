<script setup>
// Report templates (D11). Find a template, read it, and — when allowed — edit, delete or share it.
// Sharing is reviewed: the owner asks, an admin approves; once shared only admins change it,
// and an admin may withdraw it (then nobody can use it). The server enforces all of it; the
// page only offers what the server says this user may do (can_edit, actions).
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import {
  listReportTemplates, getReportTemplate, updateReportTemplate, deleteReportTemplate,
  changeTemplateSharing, ApiError,
} from '../api'
import { useAuthStore } from '../stores/auth'
import { fmtDate, fmtDateTime } from '../dates'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'
import MarkdownView from '../components/MarkdownView.vue'
import MarkdownEditor from '../components/MarkdownEditor.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const templates = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

// --- list: search + "whose" filter ---------------------------------------------------
const q = ref('')
const scope = ref('')   // '' all | mine | global | others (admins only)
const scopeOf = (x) => (x.mine ? 'mine' : x.is_global ? 'global' : 'others')
const statusFilter = ref('')
const pendingCount = computed(() => templates.value.filter((x) => x.share_status === 'pending' && x.actions.includes('approve')).length)
function showPending() { scope.value = ''; statusFilter.value = 'pending' }
const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return templates.value.filter((x) =>
    (!needle || x.name.toLowerCase().includes(needle) || x.owner.username.toLowerCase().includes(needle)) &&
    (!scope.value || scopeOf(x) === scope.value) &&
    (!statusFilter.value || x.share_status === statusFilter.value))
})

async function load() {
  loading.value = true; error.value = ''
  try { templates.value = await listReportTemplates() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

// --- selection (kept in the URL: /templates?template=<id>) -------------------------------
const selectedId = computed(() => route.query.template || null)
const detail = ref(null)
const detailError = ref('')
async function loadDetail() {
  detail.value = null; detailError.value = ''; editing.value = false
  if (!selectedId.value) return
  try { detail.value = await getReportTemplate(selectedId.value) }
  catch (e) { detailError.value = e instanceof ApiError ? e.detail : t('errors.load') }
}
watch(selectedId, loadDetail)

const statusLabel = (x) => t('tpls.status.' + x.share_status)

// --- sharing steps (only the ones the server lists for this user) --------------------------
const ACTION_ORDER = ['request', 'withdraw', 'reject', 'approve', 'unshare', 'reshare']
const PRIMARY = new Set(['request', 'approve', 'reshare'])
const CONFIRM = { request: 'tpls.confirmRequest', unshare: 'tpls.confirmUnshare' }
const sharingActions = computed(() => ACTION_ORDER.filter((a) => detail.value?.actions.includes(a)))
const acting = ref(false)
async function share(action) {
  const d = detail.value
  if (CONFIRM[action] && !confirm(t(CONFIRM[action], { name: d.name }))) return
  acting.value = true; detailError.value = ''
  try {
    const updated = await changeTemplateSharing(d.id, action)
    notice.value = t('tpls.done.' + action, { name: d.name })
    await load()
    // still visible to me? (an owner no longer sees a template an admin withdrew)
    if (templates.value.some((x) => x.id === updated.id)) detail.value = updated
    else await router.replace({ path: '/templates' })
  } catch (e) { detailError.value = e instanceof ApiError ? e.detail : t('errors.save') }
  finally { acting.value = false }
}

// --- editing ---------------------------------------------------------------------------
const editing = ref(false)
const saving = ref(false)
const draft = ref(null)
let keySeq = 0
const snapshot = ref('')
const draftState = () => JSON.stringify(draft.value && {
  ...draft.value, sections: draft.value.sections.map(({ title, content_markdown }) => ({ title, content_markdown })),
})
const dirty = computed(() => editing.value && draftState() !== snapshot.value)

function startEdit() {
  const d = detail.value
  draft.value = {
    name: d.name,
    executive_summary_md: d.executive_summary_md || '',
    introduction_md: d.introduction_md || '',
    sections: d.sections.map((s) => ({ key: ++keySeq, title: s.title, content_markdown: s.content_markdown || '' })),
  }
  snapshot.value = draftState()
  editing.value = true
  notice.value = ''; detailError.value = ''
}
const confirmDiscard = () => !dirty.value || confirm(t('tpls.discard'))
function cancelEdit() { if (confirmDiscard()) editing.value = false }

function addSection() { draft.value.sections.push({ key: ++keySeq, title: '', content_markdown: '' }) }
function moveSection(i, delta) {
  const list = draft.value.sections
  const [s] = list.splice(i, 1)
  list.splice(i + delta, 0, s)
}
function removeSection(i) { draft.value.sections.splice(i, 1) }

const blankToNull = (v) => (String(v ?? '').trim() === '' ? null : v)
async function save() {
  if (saving.value || !draft.value.name.trim()) return
  saving.value = true; detailError.value = ''
  try {
    detail.value = await updateReportTemplate(detail.value.id, {
      version: detail.value.version,
      name: draft.value.name.trim(),
      executive_summary_md: blankToNull(draft.value.executive_summary_md),
      introduction_md: blankToNull(draft.value.introduction_md),
      sections: draft.value.sections
        .filter((s) => s.title.trim())
        .map((s) => ({ title: s.title.trim(), content_markdown: blankToNull(s.content_markdown) })),
    })
    editing.value = false
    notice.value = t('tpls.saved', { name: detail.value.name })
    await load()
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      // Someone else changed it meanwhile: show their version and say why the edit was not saved.
      const message = e.detail
      await loadDetail()
      detailError.value = message
    } else detailError.value = e instanceof ApiError ? e.detail : t('errors.save')
  } finally { saving.value = false }
}

async function remove() {
  const d = detail.value
  if (!confirm(t('tpls.confirmDelete', { name: d.name }))) return
  try {
    await deleteReportTemplate(d.id)
    editing.value = false
    notice.value = t('tpls.deleted', { name: d.name })
    await router.replace({ path: '/templates' })
    await load()
  } catch (e) { detailError.value = e instanceof ApiError ? e.detail : t('errors.delete') }
}

// Moving to another template, closing the panel or leaving the page asks before dropping edits.
function select(x) {
  if (!confirmDiscard()) return
  editing.value = false
  router.replace({ path: '/templates', query: x ? { template: x.id } : {} })
}
onBeforeRouteLeave((to) => (to.path === '/templates' ? true : confirmDiscard()))

onMounted(async () => {
  document.documentElement.setAttribute('data-entity', 'reports') // templates belong to reports
  await load()
  loadDetail()
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('tpls.title') }}</h1>
        <p>{{ t('tpls.subtitle') }}</p>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="notice" class="ok msg">{{ notice }}</p>

    <div class="tplLayout" :class="{ withDetail: !!selectedId, editing }">
      <div class="listCol">
        <div class="toolbar">
          <input v-model="q" class="search" :placeholder="t('tpls.search')" />
          <select v-model="scope" class="filterSel">
            <option value="">{{ t('tpls.allScopes') }}</option>
            <option value="mine">{{ t('tpl.group.mine') }}</option>
            <option value="global">{{ t('tpl.group.global') }}</option>
            <option v-if="isAdmin" value="others">{{ t('tpl.group.others') }}</option>
          </select>
          <select v-model="statusFilter" class="filterSel">
            <option value="">{{ t('tpls.allStatuses') }}</option>
            <option v-for="s in ['private', 'pending', 'shared', ...(isAdmin ? ['unshared'] : [])]" :key="s" :value="s">
              {{ t('tpls.status.' + s) }}
            </option>
          </select>
          <button v-if="pendingCount" class="link queue" @click="showPending">{{ t('tpls.pendingQueue', { n: pendingCount }) }}</button>
          <span class="count mono">{{ filtered.length }} / {{ templates.length }}</span>
        </div>

        <section class="panel listPanel">
          <table class="ttable">
            <thead>
              <tr>
                <th>{{ t('tpls.name') }}</th>
                <th>{{ t('tpls.owner') }}</th>
                <th>{{ t('tpls.statusCol') }}</th>
                <th>{{ t('tpls.sections') }}</th>
                <th>{{ t('cols.updatedAt') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="x in filtered" :key="x.id" :class="{ sel: x.id === selectedId }" @click="select(x)">
                <td class="tname">{{ x.name }}</td>
                <td>{{ x.mine ? t('tpls.me') : x.owner.username }}</td>
                <td><span class="pill" :class="'t-' + x.share_status">{{ statusLabel(x) }}</span></td>
                <td class="mono">{{ x.section_count }}</td>
                <td class="dateCell" :title="fmtDateTime(x.updated_at)">{{ fmtDate(x.updated_at) }}</td>
              </tr>
              <tr v-if="!loading && !filtered.length">
                <td colspan="5" class="empty">{{ templates.length ? '—' : t('tpls.empty') }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <aside v-if="selectedId" class="panel detail">
        <p v-if="detailError" class="err msg">{{ detailError }}</p>
        <template v-if="detail">
          <header class="dHead">
            <h2 v-if="!editing" class="dName">{{ detail.name }}</h2>
            <input v-else v-model="draft.name" class="nameInput" maxlength="120" :aria-label="t('tpl.name')" />
            <template v-if="editing">
              <button class="btn" @click="cancelEdit">{{ t('vform.cancel') }}</button>
              <button class="btn primary" :disabled="saving || !draft.name.trim()" @click="save">{{ t('vuln.save') }}</button>
            </template>
            <template v-else>
              <button v-if="detail.can_edit" class="btn danger" @click="remove">{{ t('rowActions.delete') }}</button>
              <button v-if="detail.can_edit" class="btn primary" @click="startEdit">{{ t('rpt.edit') }}</button>
              <button class="btn" @click="select(null)">{{ t('common.close') }}</button>
            </template>
          </header>
          <dl class="facts">
            <dt>{{ t('tpls.owner') }}</dt><dd>{{ detail.mine ? t('tpls.me') : detail.owner.username }}</dd>
            <dt>{{ t('tpls.statusCol') }}</dt>
            <dd><span class="pill" :class="'t-' + detail.share_status">{{ statusLabel(detail) }}</span></dd>
            <template v-if="detail.share_requested_at && detail.share_status === 'pending'">
              <dt>{{ t('tpls.requestedAt') }}</dt><dd>{{ fmtDateTime(detail.share_requested_at) }}</dd>
            </template>
            <template v-if="detail.share_decided_by && detail.share_status !== 'pending'">
              <dt>{{ t('tpls.decidedBy') }}</dt>
              <dd>{{ detail.share_decided_by.username }} · {{ fmtDateTime(detail.share_decided_at) }}</dd>
            </template>
            <dt>{{ t('tpls.createdAt') }}</dt><dd>{{ fmtDateTime(detail.created_at) }}</dd>
            <dt>{{ t('cols.updatedAt') }}</dt><dd>{{ fmtDateTime(detail.updated_at) }}</dd>
          </dl>

          <div v-if="!editing && sharingActions.length" class="shareActs">
            <button v-for="a in sharingActions" :key="a" class="btn" :class="{ primary: PRIMARY.has(a), danger: a === 'unshare' }"
                    :disabled="acting" @click="share(a)">{{ t('tpls.action.' + a) }}</button>
          </div>

          <!-- Read -->
          <div v-if="!editing" class="content">
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.summary') }}</h3>
              <MarkdownView v-if="detail.executive_summary_md" :source="detail.executive_summary_md" />
              <p v-else class="muted">—</p>
            </section>
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.intro') }}</h3>
              <MarkdownView v-if="detail.introduction_md" :source="detail.introduction_md" />
              <p v-else class="muted">—</p>
            </section>
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.extras') }} ({{ detail.sections.length }})</h3>
              <div v-for="(s, i) in detail.sections" :key="i" class="extra">
                <h4 class="extraTitle">{{ s.title }}</h4>
                <MarkdownView v-if="s.content_markdown" :source="s.content_markdown" />
                <p v-else class="muted">—</p>
              </div>
              <p v-if="!detail.sections.length" class="muted">—</p>
            </section>
          </div>

          <!-- Edit -->
          <div v-else class="content">
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.summary') }}</h3>
              <MarkdownEditor v-model="draft.executive_summary_md" />
            </section>
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.intro') }}</h3>
              <MarkdownEditor v-model="draft.introduction_md" />
            </section>
            <section class="block">
              <h3 class="blockTitle">{{ t('rpt.extras') }} ({{ draft.sections.length }})</h3>
              <div v-for="(s, i) in draft.sections" :key="s.key" class="extraEdit">
                <div class="extraHead">
                  <input v-model="s.title" :placeholder="t('rpt.sectionTitle')" maxlength="200" />
                  <div class="extraActs">
                    <button class="link" :disabled="i === 0" @click="moveSection(i, -1)">{{ t('rpt.up') }}</button>
                    <button class="link" :disabled="i === draft.sections.length - 1" @click="moveSection(i, 1)">{{ t('rpt.down') }}</button>
                    <button class="link danger" @click="removeSection(i)">{{ t('vform.removeRef') }}</button>
                  </div>
                </div>
                <MarkdownEditor v-model="s.content_markdown" />
              </div>
              <button class="link addSection" @click="addSection">{{ t('rpt.addSection') }}</button>
            </section>
          </div>
        </template>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.tplLayout { display: grid; grid-template-columns: 1fr; gap: 16px; align-items: start; }
.tplLayout.withDetail { grid-template-columns: minmax(0, 1fr) minmax(420px, 1fr); }
/* While editing, the editors get most of the width. */
.tplLayout.withDetail.editing { grid-template-columns: minmax(0, .8fr) minmax(520px, 1.4fr); }
@media (max-width: 1100px) { .tplLayout.withDetail, .tplLayout.withDetail.editing { grid-template-columns: 1fr; } }

.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.search { flex: 1 1 200px; min-width: 160px; max-width: 320px; }
.filterSel { height: 32px; }
.count { color: var(--muted); font-size: 12px; margin-left: auto; }

.listPanel { overflow: auto; max-height: calc(100vh - 240px); }
.ttable tbody tr { cursor: pointer; }
.ttable tbody tr.sel { background: var(--accent-soft); }
.tname { color: var(--text); }
.dateCell { color: var(--muted); font-variant-numeric: tabular-nums; }
.empty { text-align: center; color: var(--muted); padding: 2rem; }
.msg { margin: 0 0 12px; font-size: 13px; }
.queue { font-size: 13px; }
.shareActs { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 14px; }
.pill.t-private { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.pill.t-pending { color: var(--st-wait-fg); background: var(--st-wait-bg); }
.pill.t-shared { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }
.pill.t-unshared { color: var(--danger); background: var(--panel-2); }
.ok { color: var(--accent); }

.detail { padding: 16px 18px 18px; position: sticky; top: 0; max-height: calc(100vh - 140px); overflow: auto; }
.dHead { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.dName { margin: 0; font-size: 18px; font-weight: 400; flex: 1; min-width: 0; }
.nameInput { flex: 1; min-width: 0; font-size: 15px; }
.facts { display: grid; grid-template-columns: 120px 1fr; gap: 6px 12px; margin: 0 0 14px; font-size: 13px; }
.facts dt { color: var(--muted); }
.facts dd { margin: 0; }
.content { border-top: 1px solid var(--line); padding-top: 12px; display: grid; gap: 16px; }
.blockTitle { margin: 0 0 8px; font-size: 14px; font-weight: 400; color: var(--text); }
.extra { margin: 0 0 12px; padding-left: 12px; border-left: 2px solid var(--line); }
.extraTitle { margin: 0 0 6px; font-size: 13px; font-weight: 500; color: var(--text-2); }
.extraEdit { margin: 0 0 14px; display: grid; gap: 8px; }
.extraHead { display: flex; gap: 10px; align-items: center; }
.extraHead input { flex: 1; min-width: 0; }
.extraActs { display: flex; gap: 10px; flex: 0 0 auto; }
.extraActs .link:disabled { opacity: .35; cursor: default; text-decoration: none; }
.addSection { justify-self: start; }
</style>
