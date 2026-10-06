<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ApiError } from '../api'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail || 'Login failed' : 'Network error'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <form class="card" @submit.prevent="submit">
      <h1>🛡️ Red Team Portal</h1>
      <p class="sub">Sign in to continue</p>

      <label>Username</label>
      <input v-model="username" autocomplete="username" autofocus />

      <label>Password</label>
      <input v-model="password" type="password" autocomplete="current-password" />

      <p v-if="error" class="error">{{ error }}</p>

      <button :disabled="busy || !username || !password">
        {{ busy ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-wrap { min-height: 100vh; display: grid; place-items: center; }
.card {
  width: 320px; display: flex; flex-direction: column; gap: .4rem;
  background: #0f1620; border: 1px solid #1f2933; border-radius: 12px;
  padding: 2rem;
}
h1 { margin: 0; font-size: 1.3rem; }
.sub { margin: 0 0 1rem; color: #7d8ea3; font-size: .9rem; }
label { font-size: .75rem; color: #9fb0c3; margin-top: .5rem; }
input {
  background: #0b0f14; border: 1px solid #1f2933; border-radius: 6px;
  padding: .55rem .6rem; color: #e6edf3; font-size: .95rem;
}
input:focus { outline: none; border-color: #3b82f6; }
button {
  margin-top: 1rem; padding: .6rem; border: 0; border-radius: 6px;
  background: #2563eb; color: white; font-weight: 600; cursor: pointer;
}
button:disabled { opacity: .5; cursor: not-allowed; }
.error { color: #f87171; font-size: .85rem; margin: .3rem 0 0; }
</style>
