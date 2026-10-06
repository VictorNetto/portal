<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { t } from '../i18n'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const expanded = ref(false)

// Nav items. `to` navigates; `soon` marks not-yet-built destinations (stubbed).
const navItems = [
  { icon: '⌂', label: 'nav.hub', to: '/hub' },
  { icon: '＋', label: 'nav.createVuln', to: '/vulnerabilities/new' },
  { icon: '＋', label: 'nav.createReport', soon: true },
  { icon: '▤', label: 'nav.rvsQueue', soon: true },
  { icon: '☷', label: 'nav.audit', soon: true },
  { icon: '♙', label: 'nav.users', soon: true },
  { icon: '⚿', label: 'nav.apiKeys', soon: true },
  { icon: '⚙', label: 'nav.settings', soon: true },
]

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
  background: #050f0e; border-bottom: 1px solid rgba(74, 130, 105, .25);
}
.hamb {
  width: var(--sidebar); height: var(--header);
  display: grid; place-items: center; border: 0; background: transparent;
  color: var(--text); font-size: 24px;
}
.brand { display: flex; align-items: center; gap: 16px; font-size: 21px; font-weight: 500; letter-spacing: .3px; }
.shield {
  width: 34px; height: 34px; border: 2px solid var(--green); border-radius: 10px;
  color: var(--green); display: grid; place-items: center;
  box-shadow: 0 0 22px rgba(66, 230, 123, .15);
}
.headRight { margin-left: auto; display: flex; align-items: center; gap: 14px; padding-right: 24px; }
.headBtn {
  border: 1px solid rgba(90, 130, 115, .35); background: #071311; border-radius: 6px;
  height: 34px; padding: 0 12px; display: flex; align-items: center; gap: 9px;
}
.headBtn.ghost:hover { border-color: var(--green); color: var(--green); }
.bell { position: relative; font-size: 20px; }
.badge {
  position: absolute; right: -7px; top: -9px; background: var(--green); color: #04210f;
  border-radius: 999px; font-size: 11px; padding: 1px 6px;
}
.avatar {
  width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--green);
  display: grid; place-items: center; color: var(--green);
}

.sidebar {
  position: fixed; top: var(--header); left: 0; bottom: 0; width: var(--sidebar);
  background: rgba(4, 15, 15, .98); z-index: 25;
  display: flex; flex-direction: column; padding-top: 18px; gap: 7px;
  border-right: 1px solid rgba(75, 126, 103, .38);
  box-shadow: 7px 0 22px rgba(0, 0, 0, .18);
  transition: width .18s ease, box-shadow .18s ease;
}
.sidebar.expanded { width: var(--sidebar-expanded); box-shadow: var(--shadow); background: rgba(5, 18, 17, .985); }
.navItem {
  height: 46px; width: 100%; display: flex; align-items: center;
  color: #d8e5dd; border: 0; background: transparent; position: relative; text-align: left;
}
.navItem:hover, .navItem.active { background: rgba(66, 230, 123, .10); color: var(--green); }
.navItem.soon { color: #5f7169; }
.navItem.soon:hover { background: rgba(90, 110, 100, .08); color: #7d8ea3; cursor: default; }
.navIcon { flex: 0 0 var(--sidebar); width: var(--sidebar); height: 46px; display: grid; place-items: center; font-size: 22px; }
.navLabel { display: none; white-space: nowrap; padding-left: 4px; }
.sidebar.expanded .navLabel { display: inline-flex; align-items: center; gap: 8px; }
.soonTag {
  font-size: 10px; color: var(--amber); border: 1px solid rgba(245, 167, 66, .4);
  border-radius: 4px; padding: 0 5px; text-transform: uppercase; letter-spacing: .03em;
}
.tip {
  display: none; position: absolute; left: calc(var(--sidebar) + 8px); top: 50%;
  transform: translateY(-50%); background: #0b211c; color: var(--text);
  padding: 6px 9px; border: 1px solid var(--line); border-radius: 6px;
  white-space: nowrap; box-shadow: var(--shadow); z-index: 40;
}
.sidebar:not(.expanded) .navItem:hover .tip { display: block; }

.main {
  position: fixed; top: var(--header); left: var(--sidebar); right: 0; bottom: 0;
  overflow: auto; padding: 28px;
}
</style>
