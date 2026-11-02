<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { t, locale, setLocale, LOCALES } from '../i18n'
import { canCreate } from '../access'
import { confirmDialog } from '../dialog'
import { hasUnsaved, mmss, sessionLeft, setDiscarding } from '../session'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const expanded = ref(false)
// While the password must be changed, navigation is locked (the router guard
// enforces it too; this just makes it visible).
const forced = computed(() => !!auth.user?.must_change_password)

// Nav items. `to` navigates; `soon` marks not-yet-built destinations (stubbed);
// `adminOnly` / `roles` hide the item from users without access; `children`
// makes a group (a flyout on the collapsed rail, indented entries when expanded);
// `bottom` pins it to the foot of the rail.
// Icons are thin outline paths (24x24 grid) — the nav rail is the only place
// icons are used.
const allNavItems = [
  { icon: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z', label: 'nav.hub', to: '/hub' },
  { icon: 'M12 5v14M5 12h14', label: 'nav.createVuln', to: '/vulnerabilities/new', writer: true },
  {
    icon: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M12 12v6M9 15h6', label: 'nav.reports', writer: true,
    children: [{ label: 'nav.createReport', to: '/reports/new' }, { label: 'nav.templates', to: '/templates' }],
  },
  { icon: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01', label: 'nav.rvsQueue', to: '/rvs-queue' },
  { icon: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z', label: 'nav.audit', to: '/audit-logs', roles: ['auditor'] },
  { icon: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4', label: 'nav.admin', to: '/audit-logs', adminOnly: true, bottom: true },
]
// The admin area: while an admin is on one of these pages the rail shows only them.
const adminItems = [
  { icon: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z', label: 'nav.audit', to: '/audit-logs' },
  { icon: 'M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM20 20v-1.5a3.5 3.5 0 0 0-2.5-3.35M15 4.2a3.5 3.5 0 0 1 0 6.6', label: 'nav.users', to: '/users' },
  { icon: 'M21 2l-2 2m-7.6 7.6a5.5 5.5 0 1 1-7.8 7.8 5.5 5.5 0 0 1 7.8-7.8zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4', label: 'nav.apiKeys', to: '/api-keys' },
  { icon: 'M19 12H5M11 6l-6 6 6 6', label: 'nav.exitAdmin', to: '/hub', bottom: true },
]
const inAdmin = computed(() =>
  auth.user?.role === 'admin' && adminItems.some((i) => i.to !== '/hub' && i.to === route.path))
const navItems = computed(() =>
  inAdmin.value ? adminItems : allNavItems.filter((i) => {
    const role = auth.user?.role
    if (i.adminOnly && role !== 'admin') return false
    if (i.roles && !i.roles.includes(role)) return false
    if (i.writer && !canCreate(auth.user)) return false
    return true
  }))

function isActive(item) {
  if (item.children) return item.children.some(isActive)
  if (!item.to) return false
  if (item.to === '/hub') {
    return route.path === '/hub' ||
      (route.path.startsWith('/vulnerabilities/') && route.path !== '/vulnerabilities/new')
  }
  return route.path === item.to
}

// The group whose flyout is pinned open by a click (hover opens it too).
const openGroup = ref(null)
function go(item) {
  if (item.soon || forced.value) return
  if (item.children) {
    if (!expanded.value) openGroup.value = openGroup.value === item.label ? null : item.label
    return
  }
  router.push(item.to)
  expanded.value = false
  openGroup.value = null
}

// Profile menu: language, profile page, sign out. Closes on any outside click.
const profileOpen = ref(false)
function onDocClick(e) {
  if (profileOpen.value && !e.target.closest('.profileWrap')) profileOpen.value = false
  // The expanded nav is transient: a click anywhere outside it collapses it.
  if (expanded.value && !e.target.closest('.sidebar')) expanded.value = false
  if (openGroup.value && !e.target.closest('.navGroup')) openGroup.value = null
}
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

function goProfile() {
  profileOpen.value = false
  router.push('/profile')
}
function goDocs() {
  profileOpen.value = false
  router.push('/docs')
}

// Asked once here, so the page's own leave guard doesn't ask again after logout.
async function signOut() {
  profileOpen.value = false
  if (hasUnsaved() && !(await confirmDialog(t('common.unsavedLeave'), { danger: true, ok: t('dialog.leave') }))) return
  setDiscarding(true)
  auth.logout()
  try { await router.push('/login') } finally { setDiscarding(false) }
}
</script>

<template>
  <nav class="sidebar" :class="{ expanded, locked: forced }" :aria-label="t('brand')"
       @mouseleave="expanded = false; openGroup = null">
    <button class="hamb" @click="expanded = !expanded" aria-label="Menu">
      <svg viewBox="0 0 24 24" class="ico"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
    </button>
    <div v-for="item in navItems" :key="item.label" :class="{ navGroup: item.children, navBottom: item.bottom, open: openGroup === item.label }">
      <button
        class="navItem"
        :class="{ active: isActive(item), soon: item.soon }"
        :aria-label="t(item.label)"
        :aria-current="isActive(item) && !item.children ? 'page' : undefined"
        :aria-haspopup="item.children ? 'menu' : undefined"
        @click="go(item)"
      >
        <span class="navIcon"><svg viewBox="0 0 24 24" class="ico"><path :d="item.icon" /></svg></span>
        <span class="navLabel">
          {{ t(item.label) }}
          <small v-if="item.soon" class="soonTag">{{ t('comingSoon') }}</small>
        </span>
        <span v-if="!item.children" class="tip">{{ t(item.label) }}</span>
      </button>
      <!-- Collapsed rail: a flyout beside the icon. Expanded rail: indented entries. -->
      <div v-if="item.children" class="subList" role="menu" :aria-label="t(item.label)">
        <div class="subTitle">{{ t(item.label) }}</div>
        <button v-for="c in item.children" :key="c.to" class="navSub" role="menuitem"
                :class="{ active: isActive(c) }" :aria-label="t(c.label)"
                :aria-current="isActive(c) ? 'page' : undefined" @click="go(c)">
          {{ t(c.label) }}
        </button>
      </div>
    </div>
  </nav>

  <header class="header">
    <span class="brand">{{ t('brand') }}</span>
    <div class="headRight profileWrap">
      <button class="profileBtn" :class="{ open: profileOpen }" @click="profileOpen = !profileOpen">
        {{ auth.user?.username }}
      </button>
      <div v-if="profileOpen" class="profileMenu">
        <div class="menuLabel">{{ t('profile.language') }}</div>
        <button v-for="l in LOCALES" :key="l.code" class="menuItem"
                :class="{ current: locale === l.code }" @click="setLocale(l.code); profileOpen = false">
          {{ l.label }}
        </button>
        <div class="sep"></div>
        <button class="menuItem" @click="goDocs">{{ t('docs.menu') }}</button>
        <button class="menuItem" @click="goProfile">{{ t('profile.menu') }}</button>
        <div class="sep"></div>
        <button class="menuItem" @click="signOut">{{ t('signOut') }}</button>
        <div class="sep"></div>
        <div class="sessionTime" :title="t('session.timeHint')">
          <span>{{ t('session.time') }}</span>
          <span class="mono">{{ mmss(sessionLeft.idle) }} / {{ mmss(sessionLeft.max) }}</span>
        </div>
      </div>
    </div>
  </header>

  <main class="main">
    <slot />
  </main>
</template>

<style scoped>
.ico { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }

.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0; width: var(--sidebar);
  background: var(--nav-bg); z-index: 40;
  display: flex; flex-direction: column;
  transition: width .15s ease;
}
.sidebar.expanded { width: var(--sidebar-expanded); }
.hamb {
  height: var(--header); width: var(--sidebar); flex: 0 0 auto;
  display: grid; place-items: center; border: 0; background: transparent; color: var(--nav-fg);
}
.hamb:hover { background: var(--nav-hover); }
.navItem {
  height: 42px; width: 100%; display: flex; align-items: center;
  color: var(--nav-fg); border: 0; background: transparent; position: relative; text-align: left;
}
.navItem:hover:not(.soon):not(.active) { background: var(--nav-hover); }
.navItem.active { background: var(--nav-active); }
.navItem.soon { opacity: .45; cursor: default; }
.sidebar.locked .navItem { opacity: .35; cursor: not-allowed; pointer-events: none; }
.navIcon { flex: 0 0 var(--sidebar); display: grid; place-items: center; }
.navLabel { display: none; white-space: nowrap; font-size: 13px; color: #d5e0ec; }
.sidebar.expanded .navLabel { display: inline-flex; align-items: center; gap: 8px; }
.soonTag { font-size: 10px; color: var(--nav-fg); border: 1px solid rgba(255,255,255,.18); border-radius: 3px; padding: 0 5px; }
.tip {
  display: none; position: absolute; left: calc(var(--sidebar) + 6px); top: 50%;
  transform: translateY(-50%); background: var(--text); color: #fff;
  padding: 4px 9px; border-radius: 3px; font-size: 12px; white-space: nowrap; z-index: 50;
}
.sidebar:not(.expanded) .navItem:hover .tip { display: block; }

/* Groups. Collapsed: the entries fly out beside the icon (padding bridges the
   gap so the pointer can travel to them). Expanded: they sit indented below. */
.navGroup { position: relative; }
.navBottom { margin-top: auto; }
.subList { display: none; }
.sidebar:not(.expanded) .navGroup:hover .subList,
.sidebar:not(.expanded) .navGroup.open .subList {
  display: block; position: absolute; left: var(--sidebar); top: 0; z-index: 50; padding-left: 6px;
}
.sidebar:not(.expanded) .subList::before {
  content: ''; position: absolute; inset: 0 0 0 6px; background: var(--nav-bg); border-radius: 3px; z-index: -1;
}
.sidebar:not(.expanded) .subList { min-width: 190px; padding-top: 4px; padding-bottom: 4px; }
.subTitle { padding: 6px 14px 4px; font-size: 11px; color: var(--nav-fg); }
.sidebar.expanded .subList { display: block; padding-bottom: 4px; }
/* Expanded, the entry itself is the selection; the group header is only a label. */
.sidebar.expanded .navGroup > .navItem { cursor: default; }
.sidebar.expanded .navGroup > .navItem.active, .sidebar.expanded .navGroup > .navItem:hover { background: transparent; }
.sidebar.expanded .subTitle { display: none; }
.navSub {
  display: block; width: 100%; height: 34px; padding: 0 14px; border: 0; background: transparent;
  text-align: left; white-space: nowrap; font-size: 13px; color: #d5e0ec;
}
.sidebar.expanded .navSub { padding-left: var(--sidebar); height: 32px; }
.navSub:hover:not(.active) { background: var(--nav-hover); }
.navSub.active { background: var(--nav-active); }
.sidebar.locked .navSub { opacity: .35; pointer-events: none; }

.header {
  height: var(--header); position: fixed; top: 0; left: var(--sidebar); right: 0;
  display: flex; align-items: center; z-index: 30; padding: 0 24px;
  background: var(--panel); border-bottom: 1px solid var(--line);
}
.brand { font-size: 15px; font-weight: 400; color: var(--text); letter-spacing: .01em; }
.headRight { margin-left: auto; position: relative; font-size: 13px; }
.profileBtn {
  height: 32px; padding: 0 12px; border: 1px solid var(--line-2); border-radius: var(--radius);
  background: var(--panel); color: var(--text-2); font-family: var(--mono); font-size: 12px; font-weight: 400;
}
.profileBtn:hover, .profileBtn.open { background: var(--hover); }
.sessionTime { display: flex; justify-content: space-between; gap: 12px; padding: 6px 12px 4px; font-size: 12px; color: var(--muted); }
.sessionTime .mono { font-family: var(--mono); color: var(--text); }
.profileMenu {
  position: absolute; right: 0; top: 38px; min-width: 190px; padding: 4px; z-index: 60;
  display: flex; flex-direction: column;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-pop);
}
.menuLabel { padding: 6px 10px 4px; font-size: 11px; color: var(--dim); }
.menuItem {
  height: 30px; border: 0; background: transparent; text-align: left; padding: 0 10px;
  border-radius: var(--radius-sm); font-size: 13px; color: var(--text-2);
}
.menuItem:hover { background: var(--hover); }
.menuItem.current { color: var(--accent); }
.sep { height: 1px; background: var(--line); margin: 4px 0; }

.main {
  position: fixed; top: var(--header); left: var(--sidebar); right: 0; bottom: 0;
  overflow: auto; padding: 28px 32px;
}
</style>
