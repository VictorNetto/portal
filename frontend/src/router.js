import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import LoginView from './views/LoginView.vue'
import HubView from './views/HubView.vue'
import VulnDetailView from './views/VulnDetailView.vue'
import UsersView from './views/UsersView.vue'

// Routes follow FRONTEND_SPEC §4.1.
const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/', redirect: '/hub' },
  { path: '/hub', name: 'hub', component: HubView },
  { path: '/vulnerabilities/new', name: 'vuln-new', component: VulnDetailView },
  { path: '/vulnerabilities/:id', name: 'vuln-detail', component: VulnDetailView },
  { path: '/users', name: 'users', component: UsersView, meta: { adminOnly: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) return { name: 'login' }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'hub' }
  if (to.meta.adminOnly && auth.user?.role !== 'admin') return { name: 'hub' }
})

export default router
