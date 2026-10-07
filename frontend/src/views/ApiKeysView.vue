<script setup>
import { ref, onMounted } from 'vue'
import { listApiKeys, createApiKey, revokeApiKey, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const keys = ref([])
const loading = ref(true)
const error = ref('')

const ROLES = ['admin', 'writer_all', 'reader_all', 'auditor']
const showCreate = ref(false)
const draft = ref({ label: '', role: 'writer_all' })
const creating = ref(false)

// The one-time plaintext shown after creation.
const newKey = ref(null)
const copied = ref(false)

async function load() {
  loading.value = true; error.value = ''
  try { keys.value = await listApiKeys() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao carregar' }
  finally { loading.value = false }
}

async function create() {
  creating.value = true; error.value = ''
  try {
    const created = await createApiKey({ ...draft.value })
    newKey.value = created
    copied.value = false
    showCreate.value = false
    draft.value = { label: '', role: 'writer_all' }
    await load()
  } catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao criar' }
  finally { creating.value = false }
}

async function copyKey() {
  try { await navigator.clipboard.writeText(newKey.value.plaintext); copied.value = true } catch { /* ignore */ }
}

async function revoke(k) {
  if (!confirm(`Revogar a chave "${k.label}"?`)) return
  error.value = ''
  try { await revokeApiKey(k.id); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : 'Falha ao revogar' }
}

const isRevoked = (k) => !!k.revoked_at

onMounted(() => {
  document.documentElement.removeAttribute('data-entity')
  load()
})
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('apiKeys.title') }}</h1>
        <p>{{ t('apiKeys.subtitle') }}</p>
      </div>
      <button class="btn primary" @click="showCreate = !showCreate">＋ {{ t('apiKeys.newKey') }}</button>
    </div>

    <!-- one-time plaintext banner -->
    <section v-if="newKey" class="panel keyReveal">
      <div class="revealTop">
        <strong>{{ newKey.label }}</strong>
        <span class="warn">{{ t('apiKeys.copyWarn') }}</span>
      </div>
      <div class="keyRow">
        <code class="plaintext">{{ newKey.plaintext }}</code>
        <button class="btn" @click="copyKey">{{ copied ? t('apiKeys.copied') : t('apiKeys.copy') }}</button>
        <button class="btn primary" @click="newKey = null">{{ t('apiKeys.done') }}</button>
      </div>
    </section>

    <section v-if="showCreate" class="panel createCard">
      <div class="createRow">
        <div class="field"><label>{{ t('apiKeys.label') }}</label>
          <input v-model="draft.label" placeholder="ex.: scanner-ci" /></div>
        <div class="field"><label>{{ t('apiKeys.role') }}</label>
          <select v-model="draft.role">
            <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
          </select></div>
        <div class="createActions">
          <button class="btn" @click="showCreate = false">{{ t('apiKeys.cancel') }}</button>
          <button class="btn primary" :disabled="creating || !draft.label" @click="create">{{ t('apiKeys.create') }}</button>
        </div>
      </div>
    </section>

    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th>{{ t('apiKeys.label') }}</th>
            <th>{{ t('apiKeys.prefix') }}</th>
            <th>{{ t('apiKeys.role') }}</th>
            <th>{{ t('apiKeys.status') }}</th>
            <th style="text-align:right">{{ t('cols.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="k in keys" :key="k.id" :class="{ dim: isRevoked(k) }">
            <td class="kname">{{ k.label }}</td>
            <td class="mono">{{ k.key_prefix }}…</td>
            <td>{{ t('roles.' + k.role) }}</td>
            <td>
              <span class="pill" :class="isRevoked(k) ? 'off' : 'on'">
                {{ isRevoked(k) ? t('apiKeys.revoked') : t('apiKeys.active') }}
              </span>
            </td>
            <td class="actions">
              <button v-if="!isRevoked(k)" class="link danger" @click="revoke(k)">{{ t('apiKeys.revoke') }}</button>
              <span v-else class="muted">—</span>
            </td>
          </tr>
          <tr v-if="!loading && !keys.length"><td colspan="5" class="empty">{{ t('apiKeys.empty') }}</td></tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<style scoped>
.pageTop { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.titleBlock h1 { margin: 0 0 4px; font-weight: 650; font-size: 24px; color: var(--text); letter-spacing: -.01em; }
.titleBlock p { margin: 0; color: var(--muted); font-size: 13px; }
.btn { border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--radius-sm); height: 36px; padding: 0 14px; color: var(--text-2); display: inline-flex; align-items: center; gap: 8px; font-weight: 500; }
.btn:hover { border-color: var(--dim); background: var(--hover); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; box-shadow: var(--shadow); }
.btn:disabled { opacity: .5; cursor: not-allowed; }

.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.keyReveal { padding: 1rem 1.3rem; margin-bottom: 16px; border-color: var(--accent); background: var(--accent-soft); }
.revealTop { display: flex; gap: 14px; align-items: baseline; margin-bottom: 10px; }
.revealTop .warn { color: var(--st-wait-fg); font-size: .8rem; }
.keyRow { display: flex; gap: 10px; align-items: center; }
.plaintext { flex: 1; font-family: var(--mono); background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: .5rem .7rem; font-size: .85rem; word-break: break-all; }

.createCard { padding: 1.1rem 1.3rem; margin-bottom: 16px; }
.createRow { display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap; }
.field { display: flex; flex-direction: column; gap: 5px; }
.field label { font-size: .78rem; color: var(--muted); }
.field input, .field select { background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm); padding: .5rem .6rem; color: var(--text); font-size: .9rem; height: 36px; }
.field input:focus, .field select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.createActions { display: flex; gap: 8px; margin-left: auto; }

table { width: 100%; border-collapse: collapse; }
th { text-align: left; color: #7a8698; font-weight: 600; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; padding: 11px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
td { padding: 12px 16px; border-bottom: 1px solid var(--line); color: var(--text-2); font-size: 13px; }
tbody tr:last-child td { border-bottom: 0; }
tr.dim td { opacity: .55; }
.kname { font-weight: 500; color: var(--text); }
.mono { font-family: var(--mono); color: var(--muted); }
.pill { font-size: 11px; padding: 3px 9px; border-radius: 999px; font-weight: 600; }
.pill.on { color: var(--st-fixed-fg); background: var(--st-fixed-bg); }
.pill.off { color: var(--st-draft-fg); background: var(--st-draft-bg); }
.actions { text-align: right; }
.link { background: none; border: 0; color: var(--accent); font-weight: 500; font-size: 13px; }
.link.danger { color: var(--danger); }
.link:hover { text-decoration: underline; }
.empty { text-align: center; color: var(--muted); padding: 2.5rem; }
.err { color: var(--danger); } .muted { color: var(--muted); }
</style>
