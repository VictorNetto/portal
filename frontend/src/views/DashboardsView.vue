<script setup>
// The dashboards (D18): one list, shared by admins and dashboard accounts.
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError, listDashboards } from '../api'
import { t } from '../i18n'
import { fmtDateTime } from '../dates'
import AppShell from '../components/AppShell.vue'

const router = useRouter()
const items = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  document.documentElement.removeAttribute('data-entity')
  try { items.value = await listDashboards() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('dash.title') }}</h1>
        <p>{{ t('dash.subtitle') }}</p>
      </div>
      <button class="btn primary" @click="router.push('/dashboards/new')">{{ t('dash.new') }}</button>
    </div>
    <p v-if="error" class="err">{{ error }}</p>
    <section class="panel">
      <table>
        <thead><tr>
          <th>{{ t('dash.name') }}</th>
          <th>{{ t('dash.charts') }}</th>
          <th>{{ t('dash.createdBy') }}</th>
          <th>{{ t('dash.updated') }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="d in items" :key="d.id" class="clickRow" @click="router.push(`/dashboards/${d.id}`)">
            <td>
              <div class="dname">{{ d.name }}</div>
              <div v-if="d.description" class="muted small">{{ d.description }}</div>
            </td>
            <td class="muted">{{ t('dash.chartCount', { n: d.chart_count }) }}<template v-if="d.screen_count > 1"> · {{ t('dash.screenCount', { n: d.screen_count }) }}</template></td>
            <td class="muted mono">{{ d.created_by }}</td>
            <td class="muted">{{ fmtDateTime(d.updated_at) }}</td>
          </tr>
          <tr v-if="!loading && !items.length"><td colspan="4" class="empty">{{ t('dash.empty') }}</td></tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<style scoped>
.clickRow { cursor: pointer; }
.clickRow:hover td { background: var(--hover); }
.dname { color: var(--text); }
.small { font-size: 12px; margin-top: 2px; }
</style>
