import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import LoginView from './views/LoginView.vue'
import HubView from './views/HubView.vue'
import VulnDetailView from './views/VulnDetailView.vue'
import UsersView from './views/UsersView.vue'
import ApiKeysView from './views/ApiKeysView.vue'
import AuditView from './views/AuditView.vue'
import ProfileView from './views/ProfileView.vue'
import TemplatesView from './views/TemplatesView.vue'
import ReportView from './views/ReportView.vue'
import DocsView from './views/DocsView.vue'
import DefenseInboxView from './views/DefenseInboxView.vue'
import DefenseVulnView from './views/DefenseVulnView.vue'
import { SECTIONS } from './defenseSections'

// Routes follow FRONTEND_SPEC §4.1.
const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/', redirect: '/hub' },
  { path: '/hub', name: 'hub', component: HubView },
  { path: '/vulnerabilities/new', name: 'vuln-new', component: VulnDetailView },
  { path: '/vulnerabilities/:id', name: 'vuln-detail', component: VulnDetailView },
  { path: '/users', name: 'users', component: UsersView, meta: { adminOnly: true } },
  { path: '/api-keys', name: 'api-keys', component: ApiKeysView, meta: { adminOnly: true } },
  { path: '/reports/new', name: 'report-new', component: ReportView },
  { path: '/reports/:id', name: 'report-detail', component: ReportView },
  { path: '/reports/:rid/vulnerabilities/new', name: 'report-vuln-new', component: VulnDetailView },
  { path: '/profile', name: 'profile', component: ProfileView },
  { path: '/docs', name: 'docs', component: DocsView },
  { path: '/templates', name: 'templates', component: TemplatesView, meta: { roles: ['admin', 'write_all', 'write_restricted'] } },
  { path: '/audit-logs', name: 'audit', component: AuditView, meta: { roles: ['admin', 'auditor'] } },
  // D17: one page per section of the defense team's work; /defense opens the first.
  { path: '/defense', name: 'defense', redirect: SECTIONS[0].path },
  ...SECTIONS.map((s) => ({
    path: s.path, name: `defense-${s.key}`, component: DefenseInboxView, meta: { roles: ['defense'], section: s.key },
  })),
  { path: '/defense/vulnerabilities/:id', name: 'defense-vuln', component: DefenseVulnView, meta: { roles: ['defense'] } },
]

// D17: a defense account has its own pages and the profile, nothing else.
const DEFENSE_ROUTES = ['defense', 'defense-vuln', 'profile', 'docs', ...SECTIONS.map((s) => `defense-${s.key}`)]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) return { name: 'login' }
  // First-login rule: until the password is changed, the profile page is the
  // only place the user can go.
  if (auth.isAuthenticated && auth.user?.must_change_password && to.name !== 'profile') {
    return { name: 'profile' }
  }
  if (auth.user?.role === 'defense' && !to.meta.public && !DEFENSE_ROUTES.includes(to.name)) return { name: 'defense' }
  if (to.name === 'login' && auth.isAuthenticated) return { name: auth.user?.role === 'defense' ? 'defense' : 'hub' }
  if (to.meta.adminOnly && auth.user?.role !== 'admin') return { name: 'hub' }
  if (to.meta.roles && !to.meta.roles.includes(auth.user?.role)) return { name: 'hub' }
})

export default router
