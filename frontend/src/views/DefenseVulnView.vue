<script setup>
// One vulnerability as the defense team sees it (D17): what the red team sent, read-only,
// plus the team's two steps: accept it, then record its RVS ID.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  defenseVuln, defenseAttachments, defenseAccept, defenseSetRvs, fetchAttachmentBlob, ApiError,
} from '../api'
import { t } from '../i18n'
import { fmtDateTime } from '../dates'
import AppShell from '../components/AppShell.vue'
import MarkdownView from '../components/MarkdownView.vue'
import AttachmentsPanel from '../components/AttachmentsPanel.vue'
import VulnTimeline from '../components/VulnTimeline.vue'

const route = useRoute()
const router = useRouter()
const vuln = ref(null)
const attachments = ref([])
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const rvs = ref('')

document.documentElement.setAttribute('data-entity', 'vulns')
onUnmounted(() => document.documentElement.removeAttribute('data-entity'))

const STEPS = [
  { key: 'sent', label: 'timeline.received', at: 'sent_at', status: 'sent' },
  { key: 'accepted', label: 'timeline.accepted', at: 'accepted_at' },
  { key: 'fixing', at: 'fixing_at', status: 'fixing' },
  { key: 'retesting', at: 'retesting_at', status: 'retesting' },
  { key: 'fixed', at: 'fixed_at', status: 'fixed' },
]
const mayAccept = computed(() => vuln.value?.status === 'sent' && !vuln.value.accepted_at)
const mayRecordRvs = computed(() => vuln.value?.status === 'sent' && !!vuln.value.accepted_at)
const sevClass = (s) => { const n = Number(s); return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo' }

async function load() {
  loading.value = true; error.value = ''
  try {
    vuln.value = await defenseVuln(route.params.id)
    try { attachments.value = await defenseAttachments(route.params.id) } catch { /* non-fatal */ }
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

async function accept() {
  busy.value = true; error.value = ''; notice.value = ''
  try { vuln.value = await defenseAccept(vuln.value.id); notice.value = t('defense.acceptedOk') }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update'); await load() }
  finally { busy.value = false }
}

async function recordRvs() {
  const value = rvs.value.trim()
  if (!value) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    vuln.value = await defenseSetRvs(vuln.value.id, value)
    rvs.value = ''
    notice.value = t('defense.rvsOk')
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.register'); await load() }
  finally { busy.value = false }
}

async function download(a) {
  try {
    const url = URL.createObjectURL(await fetchAttachmentBlob(a.id))
    const link = document.createElement('a')
    link.href = url
    link.download = a.original_filename
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch { error.value = t('errors.load') }
}

onMounted(load)
watch(() => route.params.id, (id) => { if (id) load() })
</script>

<template>
  <AppShell>
    <div class="stickyTop">
      <nav class="crumbs">
        <a @click="router.push('/defense')">{{ t('defense.title') }}</a>
        <span>›</span>
        <strong>{{ vuln?.identifier || vuln?.internal_id || '…' }}</strong>
      </nav>

      <div class="pageTop">
        <div class="titleBlock">
          <h1>{{ vuln?.identifier || '…' }}</h1>
          <p v-if="vuln">
            {{ t('status.' + vuln.status) }} · {{ t('cols.internalId') }} <span class="mono">{{ vuln.internal_id }}</span>
            <template v-if="vuln.accepter"> · {{ t('defense.acceptedBy', { user: vuln.accepter.username, when: fmtDateTime(vuln.accepted_at) }) }}</template>
          </p>
        </div>
        <div class="pageActions">
          <button v-if="mayAccept" class="btn primary" :disabled="busy" @click="accept">{{ t('defense.accept') }}</button>
        </div>
      </div>

      <p v-if="notice" class="ok msg">{{ notice }}</p>
      <p v-if="error" class="err msg">{{ error }}</p>
    </div>

    <p v-if="loading" class="muted">{{ t('vuln.loading') }}</p>
    <template v-else-if="vuln">
      <section v-if="mayRecordRvs" class="panel card">
        <h2 class="secTitle">{{ t('rvs.rvsId') }}</h2>
        <p class="hint">{{ t('defense.rvsHint') }}</p>
        <form class="rvsForm" @submit.prevent="recordRvs">
          <input v-model="rvs" :placeholder="t('rvs.placeholder')" maxlength="200" />
          <button class="btn primary" :disabled="busy || !rvs.trim()">{{ t('rvs.enter') }}</button>
        </form>
      </section>

      <section class="panel card">
        <h2 class="secTitle">{{ t('timeline.title') }}</h2>
        <VulnTimeline :vuln="vuln" :steps="STEPS" />
      </section>

      <section class="panel card">
        <h2 class="secTitle">{{ t('vform.general') }}</h2>
        <div class="infoGrid">
          <div class="f"><label>{{ t('vform.cwe') }}</label><div class="roVal">{{ vuln.cwe || '—' }}</div></div>
          <div class="f">
            <label>{{ t('vform.cvss') }}</label>
            <div class="roVal">
              <span v-if="vuln.cvss_score != null" class="cvss" :class="sevClass(vuln.cvss_score)">{{ Number(vuln.cvss_score).toFixed(1) }}</span>
              <template v-else>—</template>
            </div>
          </div>
          <div class="f"><label>{{ t('vform.cvssVector') }}</label><div class="roVal mono">{{ vuln.cvss_vector || '—' }}</div></div>
          <div class="f"><label>{{ t('defense.report') }}</label><div class="roVal">{{ vuln.report?.name || '—' }}</div></div>
        </div>
      </section>

      <div class="layout">
        <div class="stack">
          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.description') }}</h2>
            <MarkdownView :source="vuln.description || '—'" />
          </section>
          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.finding') }}</h2>
            <MarkdownView :source="vuln.finding_detail || '—'" />
          </section>
          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.mitigation') }}</h2>
            <MarkdownView :source="vuln.mitigation || '—'" />
          </section>
          <section class="panel card">
            <h2 class="secTitle">{{ t('vform.references') }}</h2>
            <ul v-if="vuln.references.length" class="refList">
              <li v-for="r in vuln.references" :key="r"><a :href="r" target="_blank" rel="noopener noreferrer">{{ r }}</a></li>
            </ul>
            <p v-else class="roVal">—</p>
          </section>
        </div>
        <div class="stack">
          <section class="panel card">
            <h2 class="secTitle">{{ t('attach.title') }}</h2>
            <AttachmentsPanel :attachments="attachments" disabled :copyable="false" @download="download" />
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
.pageActions { display: flex; gap: 8px; }
.msg { margin: 0 0 14px; font-size: 13px; }
.ok { color: var(--accent); }
.card { padding: 16px 18px 18px; margin-bottom: 16px; overflow: visible; }
.secTitle { margin: 0 0 12px; font-size: 14px; font-weight: 400; color: var(--text); }
.hint { margin: -6px 0 12px; color: var(--muted); font-size: 12px; }
.f { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.f label { font-size: 12px; color: var(--muted); }
.roVal { font-size: 14px; color: var(--text); line-height: 1.5; min-height: 21px; word-break: break-word; }
.roVal.mono, .mono { font-family: var(--mono); font-size: 13px; }
.roVal .cvss.hi { color: var(--danger); } .roVal .cvss.me { color: var(--st-wait-fg); } .roVal .cvss.lo { color: var(--muted); }
.infoGrid { display: grid; grid-template-columns: .8fr .6fr 1.4fr 1.2fr; gap: 16px 24px; align-items: start; }
.layout { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(340px, .9fr); gap: 16px; align-items: start; }
.stack { min-width: 0; }
.refList { margin: 0; padding-left: 18px; display: grid; gap: 4px; font-size: 13px; }
.refList a { color: var(--accent); word-break: break-all; }
.rvsForm { display: flex; gap: 8px; max-width: 520px; }
.rvsForm input { flex: 1; font-family: var(--mono); font-size: 13px; }
@media (max-width: 1100px) { .infoGrid, .layout { grid-template-columns: 1fr; } }
</style>
