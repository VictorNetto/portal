<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listUsers, createUser, updateUser, resetUserPassword, getUserAccess, ApiError } from '../api'
import { useAuthStore } from '../stores/auth'
import { fmtDateTime } from '../dates'
import { t } from '../i18n'
import { promptDialog } from '../dialog'
import AppShell from '../components/AppShell.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const users = ref([])
const loading = ref(true)
const error = ref('')

const ROLES = ['admin', 'write_all', 'read_all', 'write_restricted', 'read_restricted', 'auditor', 'defense', 'dashboard']
const RESTRICTED = ['write_restricted', 'read_restricted']

// --- list: search + filters ---------------------------------------------------
const q = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return users.value.filter((u) =>
    (!needle || u.username.toLowerCase().includes(needle)) &&
    (!roleFilter.value || u.role === roleFilter.value) &&
    (!statusFilter.value || (statusFilter.value === 'active') === u.is_active))
})

async function load() {
  loading.value = true; error.value = ''
  try { users.value = await listUsers() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

// --- selection (kept in the URL: /users?user=<id>) -----------------------------
const selectedId = computed(() => route.query.user || null)
const selected = computed(() => users.value.find((u) => u.id === selectedId.value) || null)
const isSelf = computed(() => selected.value?.id === auth.user?.id)
const select = (u) => router.replace({ path: '/users', query: u ? { user: u.id } : {} })

// --- access of the selected user ------------------------------------------------
const access = ref(null)
const accessTab = ref('vulns')
const accessError = ref('')
async function loadAccess() {
  access.value = null; accessError.value = ''
  if (!selected.value || !isAdmin.value) return
  try { access.value = await getUserAccess(selected.value.id) }
  catch (e) { accessError.value = e instanceof ApiError ? e.detail : t('errors.load') }
}
watch(() => [selectedId.value, selected.value?.role], loadAccess)
const accessItems = computed(() => (accessTab.value === 'vulns' ? access.value?.vulnerabilities : access.value?.reports) || [])
const openRecord = (item) => router.push(accessTab.value === 'vulns' ? `/vulnerabilities/${item.id}` : `/reports/${item.id}`)

// --- create -----------------------------------------------------------------------
const showCreate = ref(false)
const draft = ref({ username: '', password: '', role: 'read_all' })
const creating = ref(false)

async function create() {
  creating.value = true; error.value = ''
  try {
    const u = await createUser({ ...draft.value })
    showCreate.value = false
    draft.value = { username: '', password: '', role: 'read_all' }
    await load()
    select(u)
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.create') }
  finally { creating.value = false }
}

// --- changes on the selected user ---------------------------------------------------
async function changeRole(role) {
  error.value = ''
  try { await updateUser(selected.value.id, { role }); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update'); await load() }
}

async function toggleActive() {
  error.value = ''
  try { await updateUser(selected.value.id, { is_active: !selected.value.is_active }); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update') }
}

async function resetPw() {
  const pw = (await promptDialog(t('misc.resetPrompt', { user: selected.value.username })))
  if (!pw) return
  error.value = ''
  try { await resetUserPassword(selected.value.id, pw); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.reset') }
}

onMounted(async () => {
  document.documentElement.removeAttribute('data-entity') // neutral (not vuln/report)
  await load()
  loadAccess()
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('users.title') }}</h1>
        <p>{{ t('users.subtitle') }}</p>
      </div>
      <button v-if="isAdmin" class="btn primary" @click="showCreate = !showCreate">
        {{ t('users.newUser') }}
      </button>
    </div>

    <p v-if="!isAdmin" class="notice">{{ t('misc.onlyAdmins') }}</p>

    <section v-if="showCreate" class="panel formCard">
      <div class="formRow">
        <div class="field"><label>{{ t('users.username') }}</label>
          <input v-model="draft.username" /></div>
        <div class="field"><label>{{ t('users.password') }}</label>
          <input v-model="draft.password" type="password" :placeholder="t('misc.passwordPlaceholder')" /></div>
        <div class="field"><label>{{ t('users.role') }}</label>
          <select v-model="draft.role">
            <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
          </select></div>
        <div class="formActions">
          <button class="btn" @click="showCreate = false">{{ t('users.cancel') }}</button>
          <button class="btn primary" :disabled="creating || !draft.username || draft.password.length < 8" @click="create">
            {{ t('users.create') }}
          </button>
        </div>
      </div>
    </section>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="usersLayout" :class="{ withDetail: !!selected }">
      <div class="listCol">
        <div class="toolbar">
          <input v-model="q" class="search" :placeholder="t('users.search')" />
          <select v-model="roleFilter" class="filterSel">
            <option value="">{{ t('users.allRoles') }}</option>
            <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
          </select>
          <select v-model="statusFilter" class="filterSel">
            <option value="">{{ t('users.allStatuses') }}</option>
            <option value="active">{{ t('users.active') }}</option>
            <option value="inactive">{{ t('users.inactive') }}</option>
          </select>
          <span class="count mono">{{ filtered.length }} / {{ users.length }}</span>
        </div>

        <section class="panel listPanel">
          <table class="utable">
            <thead>
              <tr>
                <th>{{ t('users.username') }}</th>
                <th>{{ t('users.role') }}</th>
                <th>{{ t('users.status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in filtered" :key="u.id" :class="{ sel: u.id === selectedId }" @click="select(u)">
                <td class="uname">
                  {{ u.username }}
                  <small v-if="u.must_change_password" class="flag">{{ t('users.mustChange') }}</small>
                </td>
                <td>{{ t('roles.' + u.role) }}</td>
                <td>
                  <span class="pill" :class="u.is_active ? 'on' : 'off'">
                    {{ u.is_active ? t('users.active') : t('users.inactive') }}
                  </span>
                </td>
              </tr>
              <tr v-if="!loading && !filtered.length"><td colspan="3" class="empty">—</td></tr>
            </tbody>
          </table>
        </section>
      </div>

      <aside v-if="selected" class="panel detail">
        <header class="dHead">
          <h2 class="dName">{{ selected.username }}</h2>
          <span class="pill" :class="selected.is_active ? 'on' : 'off'">
            {{ selected.is_active ? t('users.active') : t('users.inactive') }}
          </span>
          <button class="btn" @click="select(null)">{{ t('common.close') }}</button>
        </header>

        <dl class="facts">
          <dt>{{ t('users.role') }}</dt>
          <dd>
            <select v-if="isAdmin && !isSelf" class="roleSel" :value="selected.role" @change="changeRole($event.target.value)">
              <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
            </select>
            <span v-else>{{ t('roles.' + selected.role) }}</span>
          </dd>
          <dt>{{ t('users.createdAt') }}</dt>
          <dd>{{ fmtDateTime(selected.created_at) }}</dd>
          <dt>{{ t('users.updatedAt') }}</dt>
          <dd>{{ fmtDateTime(selected.updated_at) }}</dd>
          <template v-if="selected.must_change_password">
            <dt>{{ t('users.password') }}</dt>
            <dd><span class="flag">{{ t('users.mustChange') }}</span></dd>
          </template>
        </dl>

        <div v-if="isAdmin" class="dActions">
          <button class="btn" @click="resetPw">{{ t('users.resetPassword') }}</button>
          <button v-if="!isSelf" class="btn" :class="{ danger: selected.is_active }" @click="toggleActive">
            {{ selected.is_active ? t('users.deactivate') : t('users.activate') }}
          </button>
        </div>

        <section v-if="isAdmin" class="accessBox">
          <h3 class="secTitle">{{ t('users.access') }}</h3>
          <p v-if="accessError" class="err">{{ accessError }}</p>
          <p v-else-if="access && access.scope === 'all'" class="muted">{{ t('users.accessAll') }}</p>
          <p v-else-if="access && access.scope === 'sent'" class="muted">{{ t('users.accessSent') }}</p>
          <p v-else-if="access && access.scope === 'aggregates'" class="muted">{{ t('users.accessAggregates') }}</p>
          <template v-else-if="access">
            <div class="tabs">
              <button class="tab" :class="{ active: accessTab === 'vulns' }" @click="accessTab = 'vulns'">
                {{ t('hub.tabVulns') }} ({{ access.vulnerabilities.length }})
              </button>
              <button class="tab" :class="{ active: accessTab === 'reports' }" @click="accessTab = 'reports'">
                {{ t('hub.tabReports') }} ({{ access.reports.length }})
              </button>
            </div>
            <div class="accessList">
              <table v-if="accessItems.length">
                <tbody>
                  <tr v-for="item in accessItems" :key="item.id" @click="openRecord(item)">
                    <td class="mono aId">{{ item.internal_id || '—' }}</td>
                    <td class="aTitle">
                      <span class="aName">{{ item.title || '—' }}</span>
                      <span class="rel">{{ item.relations.map((r) => t('users.rel.' + r)).join(' · ') }}</span>
                    </td>
                    <td class="aStatus"><span class="pill" :class="'s-' + item.status">{{ t((accessTab === 'vulns' ? 'status.' : 'rstatus.') + item.status) }}</span></td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="muted">{{ t('users.noAccess') }}</p>
            </div>
          </template>
        </section>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.notice { color: var(--muted); background: var(--panel-2); border: 1px solid var(--line); padding: .7rem 1rem; border-radius: var(--radius); }
.usersLayout { display: grid; grid-template-columns: 1fr; gap: 16px; align-items: start; }
.usersLayout.withDetail { grid-template-columns: minmax(0, 1fr) 460px; }
@media (max-width: 1100px) { .usersLayout.withDetail { grid-template-columns: 1fr; } }

.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.search { flex: 1 1 200px; min-width: 160px; max-width: 320px; }
.filterSel { height: 32px; }
.count { color: var(--muted); font-size: 12px; margin-left: auto; }

.listPanel { overflow: auto; max-height: calc(100vh - 260px); }
.utable tbody tr { cursor: pointer; }
.utable tbody tr.sel { background: var(--accent-soft); }
.uname { color: var(--text); }
.flag { margin-left: 8px; font-size: 11px; color: var(--st-wait-fg); background: var(--st-wait-bg); padding: 1px 6px; border-radius: var(--radius-sm); }
dd .flag { margin-left: 0; }

.detail { padding: 16px 18px 18px; position: sticky; top: 0; }
.dHead { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.dName { margin: 0; font-size: 18px; font-weight: 400; flex: 1; }
.facts { display: grid; grid-template-columns: 120px 1fr; gap: 8px 12px; margin: 0 0 14px; font-size: 13px; }
.facts dt { color: var(--muted); }
.facts dd { margin: 0; }
.roleSel { height: 28px; padding: 0 6px; }
.dActions { display: flex; gap: 8px; margin-bottom: 18px; }

.accessBox { border-top: 1px solid var(--line); padding-top: 14px; }
.secTitle { margin: 0 0 8px; font-size: 14px; font-weight: 400; }
.tabs { display: flex; gap: 20px; border-bottom: 1px solid var(--line); margin-bottom: 8px; }
.tab { border: 0; background: transparent; color: var(--muted); padding: 6px 0 7px; font-size: 13px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.accessList { max-height: calc(100vh - 520px); min-height: 120px; overflow: auto; }
.accessList tbody tr { cursor: pointer; }
.aId { white-space: nowrap; width: 84px; }
.aStatus { width: 96px; text-align: right; }
.aTitle { max-width: 0; }
.aName, .rel { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rel { color: var(--muted); font-size: 12px; }
</style>
