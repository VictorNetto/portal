<script setup>
// Create or edit a dashboard (D18): name, variables and one query per chart, each with a live preview.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ApiError, createDashboard, getDashboard, previewChart, updateDashboard } from '../api'
import { t } from '../i18n'
import { confirmDialog } from '../dialog'
import { errorText } from '../dashboards'
import { isDiscarding, useUnsaved } from '../session'
import AppShell from '../components/AppShell.vue'
import DashChart from '../components/DashChart.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id || null)

let seq = 0
const blank = () => ({ name: '', description: '', variables: [], charts: [chartRow('count where status:sent,fixing,retesting title "Abertas"')] })
function chartRow(query = '', width = 1) {
  return { key: ++seq, query, width, result: null, error: null, tvError: null, busy: false }
}
const draft = ref(blank())
const original = ref('')
const error = ref('')
const saving = ref(false)
const loaded = ref(false)

const snapshot = () => JSON.stringify({
  name: draft.value.name, description: draft.value.description || '',
  variables: draft.value.variables.map((v) => [v.name, v.value]),
  charts: draft.value.charts.map((c) => [c.query, c.width]),
})
const dirty = computed(() => loaded.value && snapshot() !== original.value)
useUnsaved(() => dirty.value)
const confirmDiscard = async () => !dirty.value || isDiscarding() ||
  (await confirmDialog(t('dash.discard'), { danger: true, ok: t('dialog.discard') }))
let leaving = false
onBeforeRouteLeave(() => leaving || confirmDiscard())
const warnUnload = (e) => { if (dirty.value && !isDiscarding()) { e.preventDefault(); e.returnValue = '' } }
onMounted(() => window.addEventListener('beforeunload', warnUnload))
onUnmounted(() => window.removeEventListener('beforeunload', warnUnload))

const variables = computed(() => draft.value.variables
  .filter((v) => v.name.trim()).map((v) => ({ name: v.name.trim(), value: v.value })))

// --- previews: each chart runs shortly after its query (or a variable) stops changing ----
const timers = new Map()
function schedule(c, delay = 450) {
  clearTimeout(timers.get(c.key))
  timers.set(c.key, setTimeout(() => preview(c), delay))
}
async function preview(c) {
  if (!c.query.trim()) { c.result = null; c.error = null; c.tvError = null; return }
  c.busy = true
  const asked = c.query
  try {
    const out = await previewChart(c.query, variables.value)
    if (asked !== c.query) return
    c.result = out.result; c.error = null; c.tvError = out.tv_error
  } catch (e) {
    if (asked !== c.query) return
    c.result = null; c.tvError = null
    c.error = e instanceof ApiError && e.detail && typeof e.detail === 'object' ? e.detail : { code: 'empty', pos: 0, params: {} }
    if (e instanceof ApiError && typeof e.detail === 'string') error.value = e.detail
  } finally { c.busy = false }
}
watch(() => JSON.stringify(variables.value), () => draft.value.charts.forEach((c) => schedule(c, 600)))

function addChart() { const c = chartRow(); draft.value.charts.push(c) }
function removeChart(i) { draft.value.charts.splice(i, 1) }
function moveChart(i, d) {
  const list = draft.value.charts
  const j = i + d
  if (j < 0 || j >= list.length) return
  ;[list[i], list[j]] = [list[j], list[i]]
}
function addVariable() { draft.value.variables.push({ name: '', value: '' }) }

async function load() {
  if (id.value) {
    try {
      const d = await getDashboard(id.value)
      draft.value = {
        name: d.name, description: d.description || '',
        variables: d.variables.map((v) => ({ ...v })),
        charts: d.charts.map((c) => chartRow(c.query, c.width)),
      }
    } catch { error.value = t('errors.load'); return }
  }
  original.value = snapshot()
  loaded.value = true
  draft.value.charts.forEach((c) => preview(c))
}

async function save() {
  error.value = ''
  if (draft.value.charts.some((c) => c.error)) { error.value = t('dash.fixErrors'); return }
  saving.value = true
  const body = {
    name: draft.value.name.trim(), description: draft.value.description.trim() || null,
    variables: variables.value,
    charts: draft.value.charts.filter((c) => c.query.trim()).map((c) => ({ query: c.query.trim(), width: c.width })),
  }
  try {
    const d = id.value ? await updateDashboard(id.value, body) : await createDashboard(body)
    leaving = true
    router.push(`/dashboards/${d.id}`)
  } catch (e) {
    const det = e instanceof ApiError ? e.detail : null
    if (det?.code === 'invalid_charts') {
      const kept = draft.value.charts.filter((c) => c.query.trim())
      det.errors.forEach((x) => { if (kept[x.chart]) kept[x.chart].error = x })
      error.value = t('dash.fixErrors')
    } else error.value = typeof det === 'string' ? det : t('errors.save')
  } finally { saving.value = false }
}
async function cancel() {
  if (!(await confirmDiscard())) return
  leaving = true
  router.push(id.value ? `/dashboards/${id.value}` : '/dashboards')
}

onMounted(() => { document.documentElement.removeAttribute('data-entity'); load() })
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ id ? t('dash.editTitle') : t('dash.newTitle') }}</h1>
        <p><router-link to="/docs#dashboards" class="helpLink">{{ t('dash.help') }}</router-link></p>
      </div>
      <div class="topActions">
        <button class="btn" @click="cancel">{{ t('dash.cancel') }}</button>
        <button class="btn primary" :disabled="saving || !draft.name.trim()" @click="save">{{ t('dash.save') }}</button>
      </div>
    </div>
    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel formCard">
      <div class="formRow">
        <div class="field grow"><label>{{ t('dash.name') }}</label><input v-model="draft.name" maxlength="120" /></div>
        <div class="field grow2"><label>{{ t('dash.description') }}</label><input v-model="draft.description" maxlength="500" /></div>
      </div>
    </section>

    <section class="panel formCard">
      <div class="secTitle">{{ t('dash.variables') }}</div>
      <p class="muted hint">{{ t('dash.variablesHint') }}</p>
      <div v-for="(v, i) in draft.variables" :key="i" class="varRow">
        <span class="dollar mono">$</span>
        <input v-model="v.name" class="mono vname" :placeholder="t('dash.varName')" :aria-label="t('dash.varName')" maxlength="40" />
        <input v-model="v.value" class="mono vvalue" :placeholder="t('dash.varValue')" :aria-label="t('dash.varValue')" maxlength="200" />
        <button class="link danger" @click="draft.variables.splice(i, 1)">{{ t('dash.remove') }}</button>
      </div>
      <div><button class="btn" @click="addVariable">{{ t('dash.addVariable') }}</button></div>
    </section>

    <div class="secTitle chartsTitle">{{ t('dash.charts') }}</div>
    <section v-for="(c, i) in draft.charts" :key="c.key" class="panel chartEdit">
      <div class="editSide">
        <div class="editTop">
          <span class="muted small">{{ t('dash.chart', { n: i + 1 }) }}</span>
          <span class="spacer"></span>
          <label class="muted small">{{ t('dash.width') }}
            <select v-model.number="c.width" class="wsel">
              <option v-for="n in [1, 2, 3]" :key="n" :value="n">{{ t('dash.widthN', { n }) }}</option>
            </select>
          </label>
          <button class="link" :disabled="i === 0" @click="moveChart(i, -1)">{{ t('dash.moveUp') }}</button>
          <button class="link" :disabled="i === draft.charts.length - 1" @click="moveChart(i, 1)">{{ t('dash.moveDown') }}</button>
          <button class="link danger" @click="removeChart(i)">{{ t('dash.remove') }}</button>
        </div>
        <textarea v-model="c.query" class="mono query" rows="4" spellcheck="false" :aria-label="t('dash.query')"
                  maxlength="1000" @input="schedule(c)"></textarea>
        <p v-if="c.error" class="err small">{{ errorText(c.error) }}</p>
        <p v-else-if="c.tvError" class="muted small">{{ t('dash.notForTv', { msg: errorText(c.tvError) }) }}</p>
      </div>
      <div class="previewSide" :class="{ busy: c.busy }">
        <DashChart v-if="c.result" :result="c.result" :height="200" />
      </div>
    </section>
    <button class="btn" @click="addChart">{{ t('dash.addChart') }}</button>
  </AppShell>
</template>

<style scoped>
.topActions { display: flex; gap: 8px; }
.helpLink { font-size: 13px; color: var(--accent); text-decoration: none; }
.helpLink:hover { text-decoration: underline; }
.formCard { display: grid; gap: 10px; }
.grow { flex: 1 1 240px; }
.grow2 { flex: 2 1 320px; }
.secTitle { font-size: 14px; color: var(--text); }
.hint { font-size: 12px; margin: -4px 0 0; }
.varRow { display: flex; gap: 8px; align-items: center; }
.dollar { color: var(--muted); }
.vname { width: 160px; }
.vvalue { flex: 1; max-width: 420px; }
.chartsTitle { margin: 6px 0 10px; }
.chartEdit { display: grid; grid-template-columns: minmax(320px, 2fr) minmax(0, 3fr); gap: 20px; padding: 14px 16px; margin-bottom: 14px; overflow: visible; }
@media (max-width: 1000px) { .chartEdit { grid-template-columns: minmax(0, 1fr); } }
.editSide { display: grid; gap: 8px; align-content: start; }
.editTop { display: flex; align-items: center; gap: 4px; }
.editTop .link { margin-left: 12px; }
.editTop .link:disabled { opacity: .35; cursor: default; text-decoration: none; }
.spacer { flex: 1; }
.small { font-size: 12px; margin: 0; }
.wsel { height: 26px; margin-left: 6px; font-size: 12px; }
.query { width: 100%; resize: vertical; font-size: 12.5px; line-height: 1.5; padding: 8px 10px; }
.previewSide { min-width: 0; transition: opacity .15s; }
.previewSide.busy { opacity: .55; }
</style>
