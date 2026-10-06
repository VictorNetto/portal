import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import LoginView from './views/LoginView.vue'
import HubView from './views/HubView.vue'
import VulnDetailView from './views/VulnDetailView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/', name: 'hub', component: HubView },
  { path: '/vulns/:id', name: 'vuln-detail', component: VulnDetailView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard: anything not marked public requires authentication.
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'hub' }
  }
})

export default router
