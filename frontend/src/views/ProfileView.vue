<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ApiError } from '../api'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const auth = useAuthStore()
const router = useRouter()
onMounted(() => document.documentElement.removeAttribute('data-entity'))

// True on first login / after an admin reset: the user can't leave until done.
const forced = computed(() => !!auth.user?.must_change_password)

const current = ref('')
const next = ref('')
const confirm = ref('')
const busy = ref(false)
const error = ref('')
const done = ref(false)

const MIN_LEN = 8

// Client-side checks mirror the server's rules so most mistakes never round-trip.
const problem = computed(() => {
  if (!next.value) return ''
  if (next.value.length < MIN_LEN) return t('profile.errShort')
  if (next.value === current.value) return t('profile.errSame')
  if (confirm.value && confirm.value !== next.value) return t('profile.errMismatch')
  return ''
})
const canSubmit = computed(() =>
  !busy.value && current.value && next.value && confirm.value && !problem.value)

// Server messages are English; map the known ones to the UI language.
function serverError(e) {
  if (!(e instanceof ApiError)) return t('errors.network')
  const map = {
    'Current password is incorrect': 'profile.errCurrent',
    'New password must be at least 8 characters': 'profile.errShort',
    'New password must differ from the current one': 'profile.errSame',
  }
  return map[e.detail] ? t(map[e.detail]) : t('errors.save')
}

async function submit() {
  if (!canSubmit.value) return
  busy.value = true; error.value = ''; done.value = false
  const wasForced = forced.value
  try {
    await auth.changePassword(current.value, next.value)
    current.value = next.value = confirm.value = ''
    done.value = true
    if (wasForced) router.push('/hub')
  } catch (e) {
    error.value = serverError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('profile.title') }}</h1>
        <p>{{ t('profile.subtitle') }}</p>
      </div>
    </div>

    <p v-if="forced" class="banner">{{ t('profile.forced') }}</p>

    <section class="panel info">
      <div class="row"><span class="muted">{{ t('profile.username') }}</span><span class="mono">{{ auth.user?.username }}</span></div>
      <div class="row"><span class="muted">{{ t('profile.role') }}</span><span>{{ auth.user?.role ? t('roles.' + auth.user.role) : '—' }}</span></div>
    </section>

    <section class="panel pwCard">
      <h2>{{ t('profile.changePassword') }}</h2>
      <form @submit.prevent="submit">
        <div class="field">
          <label>{{ t('profile.currentPassword') }}</label>
          <input v-model="current" type="password" autocomplete="current-password" />
        </div>
        <div class="field">
          <label>{{ t('profile.newPassword') }}</label>
          <input v-model="next" type="password" autocomplete="new-password" />
          <small class="hint">{{ t('profile.rules') }}</small>
        </div>
        <div class="field">
          <label>{{ t('profile.confirmPassword') }}</label>
          <input v-model="confirm" type="password" autocomplete="new-password" />
        </div>

        <p v-if="problem" class="err">{{ problem }}</p>
        <p v-else-if="error" class="err">{{ error }}</p>
        <p v-if="done" class="ok">{{ t('profile.success') }}</p>

        <button class="btn primary" :disabled="!canSubmit">
          {{ busy ? t('profile.saving') : t('profile.submit') }}
        </button>
      </form>
    </section>
  </AppShell>
</template>

<style scoped>
.banner { max-width: 420px; margin: 0 0 16px; padding: 10px 14px; border-radius: var(--radius); background: var(--st-wait-bg); color: var(--st-wait-fg); font-size: 13px; }
.info { max-width: 420px; padding: 6px 18px; margin-bottom: 16px; }
.row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.row:last-child { border-bottom: 0; }
.pwCard { max-width: 420px; padding: 18px; }
.pwCard h2 { margin: 0 0 14px; font-size: 16px; font-weight: 400; }
.pwCard .field { margin-bottom: 14px; }
.pwCard input { width: 100%; height: 36px; }
.hint { color: var(--dim); font-size: 12px; }
.ok { color: var(--accent); font-size: 13px; }
.err { font-size: 13px; }
</style>
