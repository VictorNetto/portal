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
      <h1>Portal Red Team</h1>
      <p class="sub">Entre para continuar</p>

      <label>Usuário</label>
      <input v-model="username" autocomplete="username" autofocus />

      <label>Senha</label>
      <input v-model="password" type="password" autocomplete="current-password" />

      <p v-if="error" class="error">{{ error }}</p>

      <button :disabled="busy || !username || !password">
        {{ busy ? 'Entrando…' : 'Entrar' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-wrap { min-height: 100vh; display: grid; place-items: center; background: var(--panel-2); }
.card {
  width: 340px; display: flex; flex-direction: column; gap: 4px;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 36px;
}
h1 { margin: 0; font-size: 22px; font-weight: 300; color: var(--text); }
.sub { margin: 4px 0 18px; color: var(--muted); font-size: 13px; }
label { font-size: 12px; color: var(--muted); margin-top: 10px; }
input { height: 36px; font-size: 14px; }
button {
  margin-top: 20px; height: 36px; border: 0; border-radius: var(--radius);
  background: var(--accent); color: var(--accent-contrast); font-weight: 400;
}
button:hover:not(:disabled) { filter: brightness(.93); }
button:disabled { opacity: .45; cursor: not-allowed; }
.error { color: var(--danger); font-size: 13px; margin: 6px 0 0; }
</style>
