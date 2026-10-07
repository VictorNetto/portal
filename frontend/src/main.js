import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// Restore any stored session before mounting, so the router guard sees the
// correct auth state on first navigation.
const auth = useAuthStore(pinia)
auth.init().finally(() => {
  app.use(router)
  app.mount('#app')
})

// A request was rejected because the password must be changed (e.g. an admin
// reset it while this session was open): lock the session to the profile page.
window.addEventListener('password-change-required', () => {
  if (auth.user) auth.user.must_change_password = true
  if (router.currentRoute.value.name !== 'profile') router.push({ name: 'profile' })
})
