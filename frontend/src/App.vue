<script setup>
import { RouterView } from 'vue-router'
import AppDialog from './components/AppDialog.vue'
import SessionGuard from './components/SessionGuard.vue'
</script>

<template>
  <RouterView />
  <SessionGuard />
  <AppDialog />
</template>
