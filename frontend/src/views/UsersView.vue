<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listUsers, createUser, updateUser, resetUserPassword, ApiError } from '../api'
import { useAuthStore } from '../stores/auth'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const users = ref([])
const loading = ref(true)
const error = ref('')

const ROLES = ['admin', 'write_all', 'read_all', 'write_restricted', 'read_restricted', 'auditor']

const showCreate = ref(false)
const draft = ref({ username: '', password: '', role: 'read_all' })
const creating = ref(false)

async function load() {
  loading.value = true; error.value = ''
  try { users.value = await listUsers() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

async function create() {
  creating.value = true; error.value = ''
  try {
    await createUser({ ...draft.value })
    showCreate.value = false
    draft.value = { username: '', password: '', role: 'read_all' }
    await load()
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.create') }
  finally { creating.value = false }
}

async function changeRole(u, role) {
  error.value = ''
  try { await updateUser(u.id, { role }); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update'); await load() }
}

async function toggleActive(u) {
  error.value = ''
  try { await updateUser(u.id, { is_active: !u.is_active }); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.update') }
}

async function resetPw(u) {
  const pw = prompt(t('misc.resetPrompt', { user: u.username }))
  if (!pw) return
  error.value = ''
  try { await resetUserPassword(u.id, pw); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.reset') }
}

onMounted(() => {
  document.documentElement.removeAttribute('data-entity') // neutral (not vuln/report)
  load()
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

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th>{{ t('users.username') }}</th>
            <th>{{ t('users.role') }}</th>
            <th>{{ t('users.status') }}</th>
            <th style="text-align:right">{{ t('cols.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="uname">
              {{ u.username }}
              <small v-if="u.must_change_password" class="flag">{{ t('users.mustChange') }}</small>
            </td>
            <td>
              <select v-if="isAdmin" class="roleSel" :value="u.role" @change="changeRole(u, $event.target.value)">
                <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
              </select>
              <span v-else>{{ t('roles.' + u.role) }}</span>
            </td>
            <td>
              <span class="pill" :class="u.is_active ? 'on' : 'off'">
                {{ u.is_active ? t('users.active') : t('users.inactive') }}
              </span>
            </td>
            <td class="actions">
              <template v-if="isAdmin">
                <button class="link" @click="resetPw(u)">{{ t('users.resetPassword') }}</button>
                <button class="link" :class="{ danger: u.is_active }" @click="toggleActive(u)">
                  {{ u.is_active ? t('users.deactivate') : t('users.activate') }}
                </button>
              </template>
              <span v-else class="muted">—</span>
            </td>
          </tr>
          <tr v-if="!loading && !users.length"><td colspan="4" class="empty">—</td></tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<style scoped>
.notice { color: var(--muted); background: var(--panel-2); border: 1px solid var(--line); padding: .7rem 1rem; border-radius: var(--radius); }
.uname { color: var(--text); }
.flag { margin-left: 8px; font-size: 11px; color: var(--st-wait-fg); background: var(--st-wait-bg); padding: 1px 6px; border-radius: var(--radius-sm); }
.roleSel { height: 28px; padding: 0 6px; }
.actions { text-align: right; }
</style>
