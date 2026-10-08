<script setup>
import { ref, onMounted } from 'vue'
import { listApiKeys, createApiKey, revokeApiKey, ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const keys = ref([])
const loading = ref(true)
const error = ref('')

const ROLES = ['admin', 'write_all', 'read_all', 'auditor']
const showCreate = ref(false)
const draft = ref({ label: '', role: 'write_all' })
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
    const created = await createApiKey({ ...draft.value })
    newKey.value = created
    copied.value = false
    showCreate.value = false
    draft.value = { label: '', role: 'write_all' }
    await load()
  } catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.create') }
  finally { creating.value = false }
}

async function copyKey() {
  try { await navigator.clipboard.writeText(newKey.value.plaintext); copied.value = true } catch { /* ignore */ }
}

async function revoke(k) {
  if (!confirm(t('misc.confirmRevoke', { label: k.label }))) return
  error.value = ''
  try { await revokeApiKey(k.id); await load() }
  catch (e) { error.value = e instanceof ApiError ? e.detail : t('errors.revoke') }
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
        <div class="field"><label>{{ t('apiKeys.role') }}</label>
          <select v-model="draft.role">
            <option v-for="r in ROLES" :key="r" :value="r">{{ t('roles.' + r) }}</option>
          </select></div>
        <div class="formActions">
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
.keyReveal { padding: 16px 18px; margin-bottom: 16px; border-color: var(--accent); }
.revealTop { display: flex; gap: 14px; align-items: baseline; margin-bottom: 10px; }
.revealTop .warn { color: var(--st-wait-fg); font-size: 12px; }
.keyRow { display: flex; gap: 8px; align-items: center; }
.plaintext { flex: 1; font-family: var(--mono); background: var(--panel-2); border: 1px solid var(--line-2); border-radius: var(--radius); padding: 6px 10px; font-size: 13px; word-break: break-all; }
tr.dim td { opacity: .55; }
.kname { color: var(--text); }
td.mono { color: var(--muted); }
.actions { text-align: right; }
</style>
