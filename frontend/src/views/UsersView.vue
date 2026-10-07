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

const ROLES = ['admin', 'writer_all', 'reader_all', 'auditor']

const showCreate = ref(false)
const draft = ref({ username: '', password: '', role: 'reader_all' })
const creating = ref(false)

async function load() {
  loading.value = true; error.value = ''
  try { users.value = await listUsers() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao carregar' }
  finally { loading.value = false }
}

async function create() {
  creating.value = true; error.value = ''
  try {
    await createUser({ ...draft.value })
    showCreate.value = false
    draft.value = { username: '', password: '', role: 'reader_all' }
    await load()
  } catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao criar' }
  finally { creating.value = false }
}

async function changeRole(u, role) {
  error.value = ''
  try { await updateUser(u.id, { role }); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao atualizar'; await load() }
}

async function toggleActive(u) {
  error.value = ''
  try { await updateUser(u.id, { is_active: !u.is_active }); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao atualizar' }
}

async function resetPw(u) {
  const pw = prompt(`Nova senha para ${u.username} (mín. 8 caracteres):`)
  if (!pw) return
  error.value = ''
  try { await resetUserPassword(u.id, pw); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao redefinir' }
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
        ＋ {{ t('users.newUser') }}
      </button>
    </div>

    <p v-if="!isAdmin" class="notice">Apenas administradores podem gerenciar usuários.</p>

    <section v-if="showCreate" class="panel createCard">
      <div class="createRow">
        <div class="field"><label>{{ t('users.username') }}</label>
          <input v-model="draft.username" /></div>
        <div class="field"><label>{{ t('users.password') }}</label>
          <input v-model="draft.password" type="password" placeholder="mín. 8" /></div>
        <div class="field"><label>{{ t('users.role') }}</label>
          <select v-model="draft.role">
            <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
          </select></div>
        <div class="createActions">
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
.pageTop { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.titleBlock h1 { margin: 0 0 4px; font-weight: 650; font-size: 24px; color: var(--text); letter-spacing: -.01em; }
.titleBlock p { margin: 0; color: var(--muted); font-size: 13px; }
.notice { color: var(--muted); background: var(--panel-2); border: 1px solid var(--line); padding: .7rem 1rem; border-radius: var(--radius-sm); }

.btn { border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); height: 36px; padding: 0 14px; color: var(--text-2); display: inline-flex; align-items: center; gap: 8px; font-weight: 500; }
.btn:hover { border-color: var(--dim); background: var(--hover); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; box-shadow: var(--shadow); }
.btn:disabled { opacity: .5; cursor: not-allowed; }

.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.createCard { padding: 1.1rem 1.3rem; margin-bottom: 16px; }
.createRow { display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap; }
.field { display: flex; flex-direction: column; gap: 5px; }
.field label { font-size: .78rem; color: var(--muted); }
.field input, .field select, .roleSel { background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: .5rem .6rem; color: var(--text); font-size: .9rem; height: 36px; }
.field input:focus, .field select:focus, .roleSel:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.createActions { display: flex; gap: 8px; margin-left: auto; }

table { width: 100%; border-collapse: collapse; }
th { text-align: left; color: #7a8698; font-weight: 600; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; padding: 11px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
td { padding: 12px 16px; border-bottom: 1px solid var(--line); color: var(--text-2); font-size: 13px; }
tbody tr:last-child td { border-bottom: 0; }
.uname { font-weight: 500; color: var(--text); }
.flag { margin-left: 8px; font-size: 10.5px; color: var(--st-wait-fg); background: var(--st-wait-bg); padding: 1px 6px; border-radius: 999px; font-weight: 600; }
.roleSel { height: 32px; padding: 0 8px; }
.pill { font-size: 11px; padding: 3px 9px; border-radius: 999px; font-weight: 600; }
.pill.on { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }
.pill.off { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.actions { text-align: right; }
.link { background: none; border: 0; color: var(--accent); font-weight: 500; font-size: 13px; margin-left: 14px; }
.link:hover { text-decoration: underline; }
.link.danger { color: var(--danger); }
.empty { text-align: center; color: var(--muted); padding: 2rem; }
.err { color: var(--danger); } .muted { color: var(--muted); }
</style>
