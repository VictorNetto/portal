<script setup>
// One dashboard (D18): its screens of charts (Anterior / Próxima), its variables (changeable for
// this view only) and its TV links. The numbers refresh at the dashboard's own interval.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ApiError, createDashboardLink, deleteDashboard, getDashboard, listDashboardLinks, revokeDashboardLink, runDashboard,
} from '../api'
import { t } from '../i18n'
import { fmtDateTime } from '../dates'
import { confirmDialog } from '../dialog'
import { errorText, fmtSeconds } from '../dashboards'
import AppShell from '../components/AppShell.vue'
import DashChart from '../components/DashChart.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)
const board = ref(null)
const run = ref(null)
const values = ref({})   // the variables as this view uses them
const error = ref('')
const running = ref(false)

// The screen on view, kept in the URL (?tela=2) so a reload or a shared link stays on it.
const screens = computed(() => run.value?.screens || [])
const screen = computed(() => {
  const n = Number(route.query.tela) || 1
  return Math.min(Math.max(n, 1), Math.max(screens.value.length, 1)) - 1
})
const current = computed(() => screens.value[screen.value] || null)
function go(delta) {
  const n = screens.value.length
  if (n < 2) return
  router.replace({ query: { ...route.query, tela: ((screen.value + delta + n) % n) + 1 } })
}
function onKey(e) {
  if (e.target.closest('input, textarea, select') || e.altKey || e.ctrlKey || e.metaKey) return
  if (e.key === 'ArrowRight') go(1)
  if (e.key === 'ArrowLeft') go(-1)
}
const chartCount = computed(() => (board.value?.screens || []).reduce((a, s) => a + s.charts.length, 0))

const changed = computed(() => (board.value?.variables || []).some((v) => values.value[v.name] !== v.value))

async function compute() {
  running.value = true
  error.value = ''
  try {
    const vars = changed.value ? Object.entries(values.value).map(([name, value]) => ({ name, value })) : null
    run.value = await runDashboard(id.value, vars)
  } catch (e) {
    error.value = e instanceof ApiError ? (typeof e.detail === 'string' ? e.detail : errorText(e.detail)) : t('errors.load')
  } finally { running.value = false }
}
function resetVars() {
  values.value = Object.fromEntries((board.value.variables || []).map((v) => [v.name, v.value]))
  compute()
}

async function load() {
  try {
    board.value = await getDashboard(id.value)
    values.value = Object.fromEntries((board.value.variables || []).map((v) => [v.name, v.value]))
    await Promise.all([compute(), loadLinks()])
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? t('errors.load') : t('errors.load')
  }
}

async function remove() {
  if (!(await confirmDialog(t('dash.confirmDelete', { name: board.value.name }), { danger: true, ok: t('dialog.delete') }))) return
  try { await deleteDashboard(id.value); router.push('/dashboards') }
  catch { error.value = t('errors.delete') }
}

// Recompute at the dashboard's interval while the page is open.
let timer
watch(() => board.value?.refresh_seconds, (s) => {
  clearInterval(timer)
  if (s) timer = setInterval(() => { if (!document.hidden) compute() }, s * 1000)
})
onMounted(() => {
  document.documentElement.removeAttribute('data-entity')
  window.addEventListener('keydown', onKey)
  load()
})
onUnmounted(() => { clearInterval(timer); window.removeEventListener('keydown', onKey) })

// --- TV links ---------------------------------------------------------------------------
const links = ref([])
const showLinkForm = ref(false)
const linkLabel = ref('')
const newLink = ref(null)
const copied = ref(false)
const linkError = ref('')
async function loadLinks() { links.value = await listDashboardLinks(id.value) }
async function createLink() {
  linkError.value = ''
  try {
    const l = await createDashboardLink(id.value, linkLabel.value.trim())
    newLink.value = { ...l, url: `${window.location.origin}/tv/${l.token}` }
    copied.value = false
    showLinkForm.value = false
    linkLabel.value = ''
    await loadLinks()
  } catch (e) {
    linkError.value = e?.detail?.code === 'not_for_tv'
      ? t('dash.tvRefused') + ' ' + e.detail.errors.map((x) => `${t('dash.screenN', { n: x.screen + 1 })}, ${t('dash.chart', { n: x.chart + 1 })}: ${errorText(x)}`).join('; ')
      : t('errors.create')
  }
}
async function copyLink() {
  try { await navigator.clipboard.writeText(newLink.value.url); copied.value = true } catch { /* ignore */ }
}
async function revoke(l) {
  if (!(await confirmDialog(t('dash.confirmRevoke', { label: l.label }), { danger: true, ok: t('dialog.revoke') }))) return
  try { await revokeDashboardLink(id.value, l.id); await loadLinks() } catch { linkError.value = t('errors.revoke') }
}
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ board?.name || t('dash.title') }}</h1>
        <p v-if="board?.description">{{ board.description }}</p>
      </div>
      <div v-if="board" class="topActions">
        <button class="btn" @click="router.push('/dashboards')">{{ t('dash.back') }}</button>
        <button class="btn" :disabled="running" @click="compute">{{ t('dash.refresh') }}</button>
        <button class="btn" @click="router.push(`/dashboards/${id}/edit`)">{{ t('dash.edit') }}</button>
        <button class="btn danger" @click="remove">{{ t('dash.delete') }}</button>
      </div>
    </div>
    <p v-if="error" class="err">{{ error }}</p>

    <section v-if="board?.variables?.length" class="panel vars">
      <div v-for="v in board.variables" :key="v.name" class="field">
        <label class="mono">${{ v.name }}</label>
        <input v-model="values[v.name]" class="mono" @keydown.enter="compute" />
      </div>
      <div class="varActions">
        <button class="btn primary" :disabled="running" @click="compute">{{ t('dash.apply') }}</button>
        <button v-if="changed" class="btn" @click="resetVars">{{ t('dash.reset') }}</button>
      </div>
      <p class="muted hint">{{ t('dash.viewVariablesHint') }}</p>
    </section>

    <p v-if="board && !chartCount" class="muted">{{ t('dash.noCharts') }}</p>
    <nav v-if="screens.length > 1" class="screenNav" :aria-label="t('dash.screens')">
      <button class="btn" @click="go(-1)">{{ t('dash.prev') }}</button>
      <div class="screenInfo">
        <span class="screenTitle">{{ current?.title || t('dash.screenN', { n: screen + 1 }) }}</span>
        <span class="muted">{{ t('dash.screenOf', { n: screen + 1, total: screens.length }) }}</span>
      </div>
      <button class="btn" @click="go(1)">{{ t('dash.next') }}</button>
    </nav>
    <h2 v-else-if="current?.title" class="soloTitle">{{ current.title }}</h2>
    <div v-if="current" class="grid">
      <section v-for="(c, i) in current.charts" :key="`${screen}-${i}`" class="panel card" :class="`w${c.width}`">
        <DashChart :result="c.result" :error="c.error" />
      </section>
    </div>
    <p v-if="current && !current.charts.length" class="muted">{{ t('dash.emptyScreen') }}</p>
    <p v-if="run" class="muted gen">
      {{ t('dash.generatedAt', { at: fmtDateTime(run.generated_at) }) }} ·
      {{ t('dash.refreshesEvery', { every: fmtSeconds(board.refresh_seconds) }) }}
    </p>

    <section v-if="board" class="panel links">
      <div class="linksTop">
        <div>
          <div class="secTitle">{{ t('dash.tv') }}</div>
          <p class="muted hint">{{ t('dash.tvHint') }}</p>
        </div>
        <button class="btn" @click="showLinkForm = !showLinkForm">{{ t('dash.newLink') }}</button>
      </div>
      <div v-if="newLink" class="reveal">
        <span class="warn">{{ t('dash.linkCopyWarn') }}</span>
        <div class="keyRow">
          <code class="plaintext">{{ newLink.url }}</code>
          <button class="btn" @click="copyLink">{{ copied ? t('dash.copied') : t('dash.copy') }}</button>
          <button class="btn primary" @click="newLink = null">{{ t('dash.done') }}</button>
        </div>
      </div>
      <div v-if="showLinkForm" class="formRow linkForm">
        <div class="field"><label>{{ t('dash.linkLabel') }}</label>
          <input v-model="linkLabel" :placeholder="t('dash.linkPlaceholder')" @keydown.enter="linkLabel.trim() && createLink()" /></div>
        <button class="btn primary" :disabled="!linkLabel.trim()" @click="createLink">{{ t('dash.createLink') }}</button>
      </div>
      <p v-if="linkError" class="err">{{ linkError }}</p>
      <table v-if="links.length">
        <thead><tr>
          <th>{{ t('dash.linkLabel') }}</th><th>{{ t('dash.createdBy') }}</th>
          <th>{{ t('dash.lastUsed') }}</th><th>{{ t('apiKeys.status') }}</th><th></th>
        </tr></thead>
        <tbody>
          <tr v-for="l in links" :key="l.id" :class="{ dim: l.revoked_at }">
            <td>{{ l.label }}</td>
            <td class="muted mono">{{ l.created_by }}</td>
            <td class="muted">{{ l.last_used_at ? fmtDateTime(l.last_used_at) : t('dash.never') }}</td>
            <td><span class="pill" :class="l.revoked_at ? 'off' : 'on'">{{ l.revoked_at ? t('dash.revoked') : t('dash.active') }}</span></td>
            <td class="actions"><button v-if="!l.revoked_at" class="link danger" @click="revoke(l)">{{ t('dash.revoke') }}</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted hint">{{ t('dash.noLinks') }}</p>
    </section>
  </AppShell>
</template>

<style scoped>
.topActions { display: flex; gap: 8px; }
.vars { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; padding: 14px 16px; margin-bottom: 16px; }
.vars input { width: 220px; }
.varActions { display: flex; gap: 8px; }
.vars .hint { flex-basis: 100%; margin: 0; }
.hint { font-size: 12px; }
.screenNav { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.screenInfo { flex: 1; display: flex; align-items: baseline; justify-content: center; gap: 12px; }
.screenTitle { font-size: 16px; color: var(--text); }
.screenInfo .muted { font-size: 12px; }
.soloTitle { font-size: 16px; font-weight: 400; color: var(--text); margin: 0 0 14px; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.card { padding: 16px 18px; overflow: visible; }
.w2 { grid-column: span 2; }
.w3 { grid-column: span 3; }
@media (max-width: 1100px) { .grid { grid-template-columns: minmax(0, 1fr); } .w2, .w3 { grid-column: auto; } }
.gen { font-size: 12px; margin: 10px 0 22px; }
.links { padding: 14px 16px; display: grid; gap: 10px; }
.linksTop { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.linksTop .hint { margin: 4px 0 0; }
.secTitle { font-size: 14px; color: var(--text); }
.reveal { display: grid; gap: 8px; padding: 10px 12px; border: 1px solid var(--accent); border-radius: var(--radius); }
.reveal .warn { color: var(--st-wait-fg); font-size: 12px; }
.keyRow { display: flex; gap: 8px; align-items: center; }
.plaintext { flex: 1; font-family: var(--mono); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: var(--radius); padding: 6px 10px; font-size: 12px; word-break: break-all; }
.linkForm input { width: 260px; }
tr.dim td { opacity: .55; }
.actions { text-align: right; }
</style>
