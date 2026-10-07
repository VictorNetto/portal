<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { t } from '../i18n'
import AppShell from '../components/AppShell.vue'

const auth = useAuthStore()
onMounted(() => document.documentElement.removeAttribute('data-entity'))
</script>

<template>
  <AppShell>
    <div class="pageTop">
      <div class="titleBlock">
        <h1>{{ t('profile.title') }}</h1>
        <p>{{ t('profile.placeholder') }}</p>
      </div>
    </div>

    <!-- Temporary placeholder; the real profile page comes later. -->
    <section class="panel info">
      <div class="row"><span class="muted">{{ t('profile.username') }}</span><span class="mono">{{ auth.user?.username }}</span></div>
      <div class="row"><span class="muted">{{ t('profile.role') }}</span><span>{{ auth.user?.role ? t('roles.' + auth.user.role) : '—' }}</span></div>
    </section>
  </AppShell>
</template>

<style scoped>
.info { max-width: 420px; padding: 6px 18px; }
.row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.row:last-child { border-bottom: 0; }
</style>
