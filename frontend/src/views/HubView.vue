<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ApiError } from '../api'

const auth = useAuthStore()
const router = useRouter()

const currentPw = ref('')
const newPw = ref('')
const pwMsg = ref('')
const pwErr = ref('')

function logout() {
  auth.logout()
  router.push('/login')
}

async function changePassword() {
  pwMsg.value = ''
  pwErr.value = ''
  try {
    await auth.changePassword(currentPw.value, newPw.value)
    pwMsg.value = 'Password changed.'
    currentPw.value = ''
    newPw.value = ''
  } catch (e) {
    pwErr.value = e instanceof ApiError ? e.detail || 'Failed' : 'Network error'
  }
}
</script>

<template>
  <div class="shell">
    <header>
      <span class="brand">🛡️ Red Team Portal</span>
      <span class="spacer" />
      <span class="who" v-if="auth.user">
        {{ auth.user.username }} · <em>{{ auth.user.role }}</em>
      </span>
      <button class="ghost" @click="logout">Sign out</button>
    </header>

    <main>
      <h1>Operations Hub</h1>
      <p class="muted">You are signed in. This is the authenticated workspace shell.</p>

      <section v-if="auth.user" class="panel">
        <h2>Session</h2>
        <dl>
          <dt>User ID</dt><dd>{{ auth.user.id }}</dd>
          <dt>Username</dt><dd>{{ auth.user.username }}</dd>
          <dt>Role</dt><dd>{{ auth.user.role }}</dd>
          <dt>Must change password</dt><dd>{{ auth.user.must_change_password }}</dd>
        </dl>
      </section>

      <section class="panel" :class="{ warn: auth.user?.must_change_password }">
        <h2>Change password</h2>
        <p v-if="auth.user?.must_change_password" class="warn-text">
          You must change your password before continuing.
        </p>
        <form @submit.prevent="changePassword">
          <input v-model="currentPw" type="password" placeholder="Current password" />
          <input v-model="newPw" type="password" placeholder="New password (min 8)" />
          <button :disabled="!currentPw || !newPw">Update</button>
        </form>
        <p v-if="pwMsg" class="ok">{{ pwMsg }}</p>
        <p v-if="pwErr" class="err">{{ pwErr }}</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; }
header {
  display: flex; align-items: center; gap: 1rem;
  padding: .8rem 1.2rem; background: #0f1620; border-bottom: 1px solid #1f2933;
}
.brand { font-weight: 700; }
.spacer { flex: 1; }
.who { color: #9fb0c3; font-size: .9rem; }
.who em { color: #60a5fa; font-style: normal; }
main { padding: 2rem; max-width: 720px; }
h1 { margin: 0 0 .3rem; }
.muted { color: #7d8ea3; margin-top: 0; }
.panel {
  background: #0f1620; border: 1px solid #1f2933; border-radius: 10px;
  padding: 1.2rem 1.4rem; margin-top: 1.2rem;
}
.panel.warn { border-color: #b45309; }
.warn-text { color: #fbbf24; }
h2 { margin: 0 0 .8rem; font-size: 1rem; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: .4rem 1rem; margin: 0; }
dt { color: #7d8ea3; } dd { margin: 0; }
form { display: flex; gap: .6rem; flex-wrap: wrap; margin-top: .5rem; }
input {
  background: #0b0f14; border: 1px solid #1f2933; border-radius: 6px;
  padding: .5rem .6rem; color: #e6edf3; flex: 1; min-width: 180px;
}
button {
  padding: .5rem 1rem; border: 0; border-radius: 6px;
  background: #2563eb; color: white; font-weight: 600; cursor: pointer;
}
button.ghost { background: transparent; border: 1px solid #1f2933; color: #cbd5e1; }
button:disabled { opacity: .5; cursor: not-allowed; }
.ok { color: #4ade80; } .err { color: #f87171; }
</style>
