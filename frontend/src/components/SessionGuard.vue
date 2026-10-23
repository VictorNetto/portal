<script setup>
// Enforces the session limits on screen (D12): 1 h from login, 15 min idle.
// Warns before either one ends; when the session ends with unsaved edits, asks
// for the password again so the edits can still be saved.
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ApiError } from '../api'
import { hasUnsaved, lastActivity, markActivity, sessionLeft, setDiscarding } from '../session'
import { t } from '../i18n'

const IDLE_WARN_MS = 2 * 60 * 1000   // "are you there?" before the idle end
const END_WARN_MS = 5 * 60 * 1000    // "save your work" before the 1 h end
const RENEW_EVERY_MS = 60 * 1000     // renew at most once a minute, only after activity

const auth = useAuthStore()
const router = useRouter()

const phase = ref('none')            // none | idleWarn | endWarn | reauth
const now = ref(Date.now())
const endWarned = ref(false)
const reauthUser = ref('')
const password = ref('')
const reauthError = ref('')
const busy = ref(false)
const pwInput = ref(null)
const endReason = ref('')
let renewing = false
let hadSession = false

const idleEnd = () => lastActivity() + auth.idleMs
const left = computed(() => {
  const until = phase.value === 'idleWarn' ? idleEnd() : auth.sessionEnd
  const s = Math.max(0, Math.ceil((until - now.value) / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})

async function endSession(reason) {
  if (phase.value === 'reauth' || !hadSession) return
  hadSession = false
  endReason.value = reason
  if (hasUnsaved() && auth.user) {
    reauthUser.value = auth.user.username
    auth.logout({ keepUser: true })
    password.value = ''
    reauthError.value = ''
    phase.value = 'reauth'
    await nextTick()
    pwInput.value?.focus()
    return
  }
  phase.value = 'none'
  auth.logout()
  router.push({ name: 'login', query: { expired: reason } })
}

function tick() {
  now.value = Date.now()
  if (phase.value === 'reauth') return
  auth.syncFromStorage()                           // another tab may have renewed or signed out
  if (!auth.isAuthenticated) {
    if (hadSession) endSession('signout')
    phase.value = 'none'
    return
  }
  hadSession = true
  const n = now.value
  sessionLeft.idle = idleEnd() - n
  sessionLeft.max = auth.sessionEnd ? auth.sessionEnd - n : 0
  if (auth.sessionEnd && n >= auth.sessionEnd) return endSession('max')
  if (n >= idleEnd()) return endSession('idle')

  if (idleEnd() - n <= IDLE_WARN_MS) phase.value = 'idleWarn'
  else if (phase.value === 'idleWarn') phase.value = 'none'   // active again (maybe in another tab)
  if (phase.value === 'none' && !endWarned.value && auth.sessionEnd && auth.sessionEnd - n <= END_WARN_MS) {
    endWarned.value = true
    phase.value = 'endWarn'
  }

  // Keep the server-side idle window in step with real activity.
  if (!renewing && lastActivity() > auth.lastRenewed() && n - auth.lastRenewed() >= RENEW_EVERY_MS) {
    renewing = true
    auth.refresh().then((ok) => { if (!ok) endSession('server') }).finally(() => { renewing = false })
  }
}

function onActivity() {
  // While a session modal is up, only its buttons count as "still here".
  if (phase.value === 'idleWarn' || phase.value === 'reauth' || !auth.isAuthenticated) return
  const n = Date.now()
  if (n - lastActivity() > 1000) markActivity(n)
}

function stay() { markActivity(); phase.value = 'none'; tick() }

async function reauth() {
  busy.value = true
  reauthError.value = ''
  try {
    await auth.login(reauthUser.value, password.value)
    password.value = ''
    endWarned.value = false
    hadSession = true
    phase.value = 'none'
  } catch (e) {
    reauthError.value = e instanceof ApiError && e.status === 401 ? t('session.wrongPassword') : t('errors.network')
  } finally {
    busy.value = false
  }
}

async function discard() {
  phase.value = 'none'
  setDiscarding(true)
  auth.logout()
  try { await router.push({ name: 'login', query: { expired: endReason.value } }) } finally { setDiscarding(false) }
}

async function signOutNow() {
  phase.value = 'none'
  hadSession = false
  setDiscarding(true)                               // they chose to leave; the edits go
  auth.logout()
  try { await router.push({ name: 'login' }) } finally { setDiscarding(false) }
}

const onExpired = () => endSession('server')
const EVENTS = ['mousedown', 'mousemove', 'keydown', 'wheel', 'touchstart', 'scroll']
let timer = null
onMounted(() => {
  EVENTS.forEach((e) => window.addEventListener(e, onActivity, { passive: true, capture: true }))
  window.addEventListener('session-expired', onExpired)
  timer = setInterval(tick, 1000)
  tick()
})
onUnmounted(() => {
  EVENTS.forEach((e) => window.removeEventListener(e, onActivity, { capture: true }))
  window.removeEventListener('session-expired', onExpired)
  clearInterval(timer)
})
</script>

<template>
  <div v-if="phase !== 'none'" class="modalBack sessionModal">
    <section v-if="phase === 'idleWarn'" class="panel modal" role="alertdialog" aria-modal="true" :aria-label="t('session.idleTitle')">
      <h2 class="secTitle">{{ t('session.idleTitle') }}</h2>
      <p class="sMsg">{{ t('session.idleBody', { left }) }}</p>
      <div class="modalActions">
        <button class="btn" @click="signOutNow">{{ t('session.signOut') }}</button>
        <button class="btn primary" autofocus @click="stay">{{ t('session.stay') }}</button>
      </div>
    </section>

    <section v-else-if="phase === 'endWarn'" class="panel modal" role="alertdialog" aria-modal="true" :aria-label="t('session.endTitle')">
      <h2 class="secTitle">{{ t('session.endTitle') }}</h2>
      <p class="sMsg">{{ t('session.endBody', { left }) }}</p>
      <div class="modalActions">
        <button class="btn primary" autofocus @click="phase = 'none'">{{ t('session.gotIt') }}</button>
      </div>
    </section>

    <form v-else class="panel modal" role="alertdialog" aria-modal="true" :aria-label="t('session.reauthTitle')"
          @submit.prevent="reauth">
      <h2 class="secTitle">{{ t('session.reauthTitle') }}</h2>
      <p class="sMsg">{{ t('session.reauthBody') }}</p>
      <div class="f">
        <label>{{ t('login.username') }}</label>
        <div class="roVal">{{ reauthUser }}</div>
      </div>
      <div class="f">
        <label>{{ t('login.password') }}</label>
        <input ref="pwInput" v-model="password" type="password" autocomplete="current-password" />
      </div>
      <p v-if="reauthError" class="err">{{ reauthError }}</p>
      <div class="modalActions">
        <button type="button" class="btn danger" @click="discard">{{ t('session.discard') }}</button>
        <button type="submit" class="btn primary" :disabled="busy || !password">{{ t('session.reauth') }}</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.sessionModal { z-index: 90; }
.sMsg { margin: 0; font-size: 14px; line-height: 1.5; color: var(--text); }
.f { display: grid; gap: 4px; }
.f label { font-size: 12px; color: var(--muted); }
.roVal { font-size: 14px; color: var(--text); }
.err { margin: 0; font-size: 13px; color: var(--danger); }
</style>
