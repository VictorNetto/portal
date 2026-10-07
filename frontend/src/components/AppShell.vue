<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { t } from '../i18n'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const expanded = ref(false)

// Nav items. `to` navigates; `soon` marks not-yet-built destinations (stubbed);
// `adminOnly` hides the item from non-admins.
const allNavItems = [
  { icon: '⌂', label: 'nav.hub', to: '/hub' },
  { icon: '＋', label: 'nav.createVuln', to: '/vulnerabilities/new' },
  { icon: '＋', label: 'nav.createReport', soon: true },
  { icon: '▤', label: 'nav.rvsQueue', to: '/rvs-queue' },
  { icon: '☷', label: 'nav.audit', soon: true },
  { icon: '♙', label: 'nav.users', to: '/users', adminOnly: true },
  { icon: '⚿', label: 'nav.apiKeys', soon: true, adminOnly: true },
  { icon: '⚙', label: 'nav.settings', soon: true },
]
const navItems = computed(() =>
  allNavItems.filter((i) => !i.adminOnly || auth.user?.role === 'admin'))

function isActive(item) {
  if (!item.to) return false
  if (item.to === '/hub') return route.path === '/hub' || route.path.startsWith('/vulnerabilities/')
  return route.path === item.to
}

function go(item) {
  if (item.soon) return
  router.push(item.to)
  expanded.value = false
}

function initials(name) {
  return (name || '?').slice(0, 2).toUpperCase()
}

function signOut() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="header">
    <button class="hamb" @click="expanded = !expanded" aria-label="Menu">☰</button>
    <div class="brand">
      <div class="shield">⌁</div>
      <span class="mono">{{ t('brand') }}</span>
    </div>
    <div class="headRight">
      <button class="headBtn">◎ PT-BR ⌄</button>
      <div class="bell">♧<span class="badge">0</span></div>
      <div class="avatar mono">{{ initials(auth.user?.username) }}</div>
      <button class="headBtn ghost" @click="signOut">{{ t('signOut') }}</button>
    </div>
  </header>

  <nav class="sidebar" :class="{ expanded }" @mouseleave="expanded = false">
    <button
      v-for="item in navItems"
      :key="item.label"
      class="navItem"
      :class="{ active: isActive(item), soon: item.soon }"
      @click="go(item)"
    >
      <span class="navIcon">{{ item.icon }}</span>
      <span class="navLabel">
        {{ t(item.label) }}
        <small v-if="item.soon" class="soonTag">{{ t('comingSoon') }}</small>
      </span>
      <span class="tip">{{ t(item.label) }}</span>
    </button>
  </nav>

  <main class="main">
    <slot />
  </main>
</template>

<style scoped>
.header {
  height: var(--header); position: fixed; inset: 0 0 auto 0;
  display: flex; align-items: center; z-index: 30;
  background: var(--panel); border-bottom: 1px solid var(--line);
}
.hamb {
  width: var(--sidebar); height: var(--header);
  display: grid; place-items: center; border: 0; background: transparent;
  color: var(--muted); font-size: 20px;
}
.hamb:hover { color: var(--text); }
.brand { display: flex; align-items: center; gap: 12px; font-size: 16px; font-weight: 600; color: var(--text); }
.shield {
  width: 28px; height: 28px; background: var(--accent); border-radius: 8px;
  color: #fff; display: grid; place-items: center; font-size: 15px;
}
.headRight { margin-left: auto; display: flex; align-items: center; gap: 12px; padding-right: 20px; }
.headBtn {
  border: 1px solid var(--line-2); background: var(--panel); border-radius: 8px;
  height: 32px; padding: 0 12px; display: flex; align-items: center; gap: 8px; color: var(--muted);
}
.headBtn:hover { color: var(--text); border-color: var(--dim); }
.bell { position: relative; font-size: 18px; color: var(--muted); }
.badge {
  position: absolute; right: -7px; top: -9px; background: var(--accent); color: #fff;
  border-radius: 999px; font-size: 10px; padding: 1px 6px;
}
.avatar {
  width: 30px; height: 30px; border-radius: 50%; background: var(--accent-soft);
  display: grid; place-items: center; color: var(--accent); font-size: 12px; font-weight: 600;
}

.sidebar {
  position: fixed; top: var(--header); left: 0; bottom: 0; width: var(--sidebar);
  background: var(--panel); z-index: 25;
  display: flex; flex-direction: column; padding-top: 12px; gap: 4px;
  border-right: 1px solid var(--line);
  transition: width .18s ease, box-shadow .18s ease;
}
.sidebar.expanded { width: var(--sidebar-expanded); box-shadow: var(--shadow-pop); }
.navItem {
  height: 42px; width: 100%; display: flex; align-items: center;
  color: var(--muted); border: 0; background: transparent; position: relative; text-align: left;
}
.navItem:hover { background: var(--hover); color: var(--text); }
.navItem.active { color: var(--accent); }
.navItem.active .navIcon { background: var(--accent-soft); border-radius: 8px; }
.navItem.soon { color: var(--dim); }
.navItem.soon:hover { background: transparent; color: var(--dim); cursor: default; }
.navIcon {
  flex: 0 0 var(--sidebar); width: 40px; height: 36px; margin: 0 8px;
  display: grid; place-items: center; font-size: 19px;
}
.navLabel { display: none; white-space: nowrap; padding-left: 2px; }
.sidebar.expanded .navLabel { display: inline-flex; align-items: center; gap: 8px; }
.soonTag {
  font-size: 9.5px; color: var(--muted); border: 1px solid var(--line-2);
  border-radius: 4px; padding: 0 5px; text-transform: uppercase; letter-spacing: .03em;
}
.tip {
  display: none; position: absolute; left: calc(var(--sidebar) + 6px); top: 50%;
  transform: translateY(-50%); background: var(--text); color: #fff;
  padding: 5px 9px; border-radius: 6px; font-size: 12px;
  white-space: nowrap; box-shadow: var(--shadow-pop); z-index: 40;
}
.sidebar:not(.expanded) .navItem:hover .tip { display: block; }

.main {
  position: fixed; top: var(--header); left: var(--sidebar); right: 0; bottom: 0;
  overflow: auto; padding: 28px;
}
</style>
