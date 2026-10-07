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
      <h1>⌁ Portal Red Team</h1>
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
  width: 340px; display: flex; flex-direction: column; gap: .4rem;
  background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
  padding: 2.4rem; box-shadow: var(--shadow-pop);
}
h1 { margin: 0; font-size: 1.25rem; font-weight: 650; color: var(--text); }
.sub { margin: .2rem 0 1.2rem; color: var(--muted); font-size: .9rem; }
label { font-size: .78rem; color: var(--muted); margin-top: .6rem; }
input {
  background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm);
  padding: .6rem .7rem; color: var(--text); font-size: .95rem;
}
input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
button {
  margin-top: 1.2rem; padding: .65rem; border: 0; border-radius: var(--radius-sm);
  background: var(--accent); color: #fff; font-weight: 600; box-shadow: var(--shadow);
}
button:disabled { opacity: .5; cursor: not-allowed; }
.error { color: var(--danger); font-size: .85rem; margin: .4rem 0 0; }
</style>
