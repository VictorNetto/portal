<script setup>
import { ref, onMounted } from 'vue'
import { listApiKeys, createApiKey, revokeApiKey, ApiError } from '../api'
import { t } from '../i18n'
import { confirmDialog } from '../dialog'
import AppShell from '../components/AppShell.vue'
import { fmtDateTime } from '../dates'

const keys = ref([])
const loading = ref(true)
const error = ref('')

// What a key may do (backend app/scopes.py, D13).
const SCOPES = ['vulns:read', 'vulns:write', 'rvs:write', 'reports:read', 'exports']
const blank = () => ({ label: '', scopes: new Set(), expires: '' })
const showCreate = ref(false)
const draft = ref(blank())
const today = new Date().toISOString().slice(0, 10)
function toggleScope(s) {
  const set = new Set(draft.value.scopes)
  set.has(s) ? set.delete(s) : set.add(s)
  draft.value.scopes = set
}
const creating = ref(false)

// The one-time plaintext shown after creation.
const newKey = ref(null)
const copied = ref(false)

async function load() {
  loading.value = true; error.value = ''
  try { keys.value = await listApiKeys() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.load') }
  finally { loading.value = false }
}

async function create() {
  creating.value = true; error.value = ''
  try {
    const d = draft.value
    const created = await createApiKey({
      label: d.label, scopes: [...d.scopes],
      // The key works through the whole chosen day (UTC).
      expires_at: d.expires ? `${d.expires}T23:59:59` : null,
    })
    newKey.value = created
    copied.value = false
    showCreate.value = false
    draft.value = blank()
    await load()
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.create') }
  finally { creating.value = false }
}

async function copyKey() {
  try { await navigator.clipboard.writeText(newKey.value.plaintext); copied.value = true } catch { /* ignore */ }
}

async function revoke(k) {
  if (!(await confirmDialog(t('misc.confirmRevoke', { label: k.label }), { danger: true, ok: t('dialog.revoke') }))) return
  error.value = ''
  try { await revokeApiKey(k.id); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.revoke') }
}

const isRevoked = (k) => !!k.revoked_at
const isExpired = (k) => !!k.expires_at && new Date(k.expires_at + 'Z') <= new Date()
const state = (k) => (isRevoked(k) ? 'revoked' : isExpired(k) ? 'expired' : 'active')

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
      <button class="btn primary" @click="showCreate = !showCreate">{{ t('apiKeys.newKey') }}</button>
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

    <section v-if="showCreate" class="panel formCard">
      <div class="formRow">
        <div class="field"><label>{{ t('apiKeys.label') }}</label>
          <input v-model="draft.label" :placeholder="t('misc.keyPlaceholder')" /></div>
        <div class="field"><label>{{ t('apiKeys.expires') }}</label>
          <input v-model="draft.expires" type="date" :min="today" /></div>
      </div>
      <div class="field">
        <label>{{ t('apiKeys.scopes') }}</label>
        <div class="scopeList">
          <label v-for="s in SCOPES" :key="s" class="scope">
            <input type="checkbox" :checked="draft.scopes.has(s)" @change="toggleScope(s)" />
            <span class="mono">{{ s }}</span>
            <span class="muted">{{ t('apiKeys.scope.' + s) }}</span>
          </label>
        </div>
      </div>
      <div class="formActions">
        <button class="btn" @click="showCreate = false">{{ t('apiKeys.cancel') }}</button>
        <button class="btn primary" :disabled="creating || !draft.label || !draft.scopes.size" @click="create">{{ t('apiKeys.create') }}</button>
      </div>
    </section>

    <p v-if="error" class="err">{{ error }}</p>

    <section class="panel">
      <table>
        <thead>
          <tr>
            <th>{{ t('apiKeys.label') }}</th>
            <th>{{ t('apiKeys.prefix') }}</th>
            <th>{{ t('apiKeys.scopes') }}</th>
            <th>{{ t('apiKeys.expires') }}</th>
            <th>{{ t('apiKeys.lastUsed') }}</th>
            <th>{{ t('apiKeys.status') }}</th>
            <th style="text-align:right">{{ t('cols.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="k in keys" :key="k.id" :class="{ dim: state(k) !== 'active' }">
            <td class="kname">{{ k.label }}</td>
            <td class="mono">{{ k.key_prefix }}…</td>
            <td><div class="scopes"><span v-for="s in k.scopes" :key="s" class="mono scopeTag">{{ s }}</span>
              <span v-if="!k.scopes.length" class="muted">—</span></div></td>
            <td class="muted">{{ k.expires_at ? fmtDateTime(k.expires_at) : t('apiKeys.never') }}</td>
            <td class="muted">{{ k.last_used_at ? fmtDateTime(k.last_used_at) : '—' }}</td>
            <td>
              <span class="pill" :class="state(k) === 'active' ? 'on' : 'off'">{{ t('apiKeys.' + state(k)) }}</span>
            </td>
            <td class="actions">
              <button v-if="!isRevoked(k)" class="link danger" @click="revoke(k)">{{ t('apiKeys.revoke') }}</button>
              <span v-else class="muted">—</span>
            </td>
          </tr>
          <tr v-if="!loading && !keys.length"><td colspan="7" class="empty">{{ t('apiKeys.empty') }}</td></tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>

<style scoped>
.keyReveal { padding: 16px 18px; margin-bottom: 16px; border-color: var(--accent); }
.revealTop { display: flex; gap: 14px; align-items: baseline; margin-bottom: 10px; }
.revealTop .warn { color: var(--st-wait-fg); font-size: 12px; }
.keyRow { display: flex; gap: 8px; align-items: center; }
.plaintext { flex: 1; font-family: var(--mono); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: var(--radius); padding: 6px 10px; font-size: 13px; word-break: break-all; }
tr.dim td { opacity: .55; }
.kname { color: var(--text); }
td.mono { color: var(--muted); }
.actions { text-align: right; }
.formCard { display: grid; gap: 12px; }
.scopeList { display: grid; gap: 6px; }
.scope { display: flex; gap: 10px; align-items: center; font-size: 13px; cursor: pointer; }
.scope .mono { min-width: 110px; color: var(--text); }
.scopes { display: flex; flex-wrap: wrap; gap: 4px; }
.scopeTag { font-size: 11px; padding: 1px 6px; border: 1px solid var(--line-2); border-radius: var(--radius-sm); color: var(--text-2); }
</style>
