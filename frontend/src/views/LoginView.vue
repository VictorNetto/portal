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
.login-wrap { min-height: 100vh; display: grid; place-items: center; }
.card {
  width: 330px; display: flex; flex-direction: column; gap: .4rem;
  background: rgba(7, 19, 17, .9); border: 1px solid var(--line2); border-radius: var(--radius);
  padding: 2.2rem; box-shadow: var(--shadow);
}
h1 { margin: 0; font-size: 1.3rem; font-family: var(--mono); color: #f0fff6; }
.sub { margin: 0 0 1rem; color: var(--muted); font-size: .9rem; }
label { font-size: .75rem; color: var(--muted); margin-top: .5rem; }
input {
  background: #0b0f14; border: 1px solid var(--line); border-radius: 6px;
  padding: .55rem .6rem; color: var(--text); font-size: .95rem; font-family: var(--mono);
}
input:focus { outline: none; border-color: var(--green); }
button {
  margin-top: 1rem; padding: .6rem; border: 1px solid #4df587; border-radius: 6px;
  background: linear-gradient(180deg, #48df7d, #2fbf68); color: #03120a; font-weight: 600;
}
button:disabled { opacity: .5; cursor: not-allowed; }
.error { color: var(--red); font-size: .85rem; margin: .3rem 0 0; }
</style>
