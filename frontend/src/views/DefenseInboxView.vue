<script setup>
// The defense team's list (D17): every vulnerability sent to it, grouped by what is
// still expected from the team: accept it, then record its RVS ID.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { defenseVulns, ApiError } from '../api'
import { t } from '../i18n'
import { fmtDateTime } from '../dates'
import AppShell from '../components/AppShell.vue'

const router = useRouter()
const items = ref([])
const loading = ref(true)
const error = ref('')

const TABS = [
  { key: 'new', test: (v) => v.status === 'sent' && !v.accepted_at },
  { key: 'awaitingRvs', test: (v) => v.status === 'sent' && !!v.accepted_at },
  { key: 'inProgress', test: (v) => ['fixing', 'retesting'].includes(v.status) },
  { key: 'fixed', test: (v) => v.status === 'fixed' },
  { key: 'all', test: () => true },
]
const tab = ref('new')
const count = (key) => items.value.filter(TABS.find((x) => x.key === key).test).length
const rows = computed(() => items.value.filter(TABS.find((x) => x.key === tab.value).test))

const sevClass = (s) => { const n = Number(s); return n >= 7 ? 'hi' : n >= 4 ? 'me' : 'lo' }
// Where the vuln stands for the defense team; "sent" is split by acceptance.
const stateLabel = (v) => (v.status === 'sent' ? t(v.accepted_at ? 'defense.awaitingRvs' : 'defense.new') : t('status.' + v.status))

async function load() {
  loading.value = true; error.value = ''
  try {
    items.value = await defenseVulns()
    // Nothing new to accept: open on the first group with work in it.
    if (!count('new')) tab.value = count('awaitingRvs') ? 'awaitingRvs' : 'all'
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

onMounted(() => {
  document.documentElement.setAttribute('data-entity', 'vulns')
  load()
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('defense.title') }}</h1>
        <p>{{ t('defense.subtitle') }}</p>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="tabs">
      <button v-for="x in TABS" :key="x.key" class="tab" :class="{ active: tab === x.key }" @click="tab = x.key">
        {{ t('defense.tabs.' + x.key) }} <span class="n">{{ count(x.key) }}</span>
      </button>
    </div>

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th>{{ t('cols.internalId') }}</th>
            <th>{{ t('cols.identifier') }}</th>
            <th>{{ t('cols.cvss') }}</th>
            <th>{{ t('defense.report') }}</th>
            <th>{{ t('defense.receivedAt') }}</th>
            <th>{{ t('defense.state') }}</th>
            <th>{{ t('rvs.rvsId') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in rows" :key="v.id" class="row" @click="router.push(`/defense/vulnerabilities/${v.id}`)">
            <td class="idcell">{{ v.internal_id }}</td>
            <td>{{ v.identifier || '—' }}</td>
            <td>
              <span v-if="v.cvss_score != null" class="cvss" :class="sevClass(v.cvss_score)">{{ Number(v.cvss_score).toFixed(1) }}</span>
              <span v-else>—</span>
            </td>
            <td class="muted">{{ v.report?.name || '—' }}</td>
            <td class="muted">{{ fmtDateTime(v.sent_at) }}</td>
            <td><span class="pill" :class="'s-' + v.status">{{ stateLabel(v) }}</span></td>
            <td class="mono">{{ v.rvs_id || '—' }}</td>
          </tr>
          <tr v-if="!loading && !rows.length"><td colspan="7" class="empty">{{ t('defense.empty') }}</td></tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<style scoped>
.tabs { display: flex; gap: 24px; border-bottom: 1px solid var(--line); margin-bottom: 16px; }
.tab { border: 0; background: transparent; color: var(--muted); padding: 10px 0 9px; font-size: 14px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab:hover:not(.active) { color: var(--text); }
.tab.active { color: var(--text); border-color: var(--accent); }
.tab .n { margin-left: 4px; font-size: 12px; color: var(--dim); }
.row { cursor: pointer; }
.mono { font-family: var(--mono); font-size: 12px; }
</style>
