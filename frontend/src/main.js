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
