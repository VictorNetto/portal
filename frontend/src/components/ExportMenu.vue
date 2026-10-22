<script setup>
// One "Exportar" button that opens the list of export formats (detail pages).
import { ref, onMounted, onUnmounted } from 'vue'
import { t } from '../i18n'

defineProps({
  // [{ format: 'pdf', label: 'PDF' }, ...]
  options: { type: Array, required: true },
})
const emit = defineEmits(['export'])

const open = ref(false)
const root = ref(null)

function pick(format) {
  open.value = false
  emit('export', format)
}

const onDoc = (e) => { if (open.value && root.value && !root.value.contains(e.target)) open.value = false }
const onKey = (e) => { if (e.key === 'Escape') open.value = false }
onMounted(() => { document.addEventListener('click', onDoc); document.addEventListener('keydown', onKey) })
onUnmounted(() => { document.removeEventListener('click', onDoc); document.removeEventListener('keydown', onKey) })
</script>

<template>
  <div ref="root" class="exportWrap">
    <button type="button" class="btn" :aria-expanded="open" @click.stop="open = !open">{{ t('export.button') }}</button>
    <div v-if="open" class="exportMenu" role="menu">
      <button v-for="o in options" :key="o.format" type="button" role="menuitem" @click="pick(o.format)">
        {{ o.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.exportWrap { position: relative; display: inline-block; }
.exportMenu { position: absolute; top: calc(100% + 4px); right: 0; z-index: 30; min-width: 170px; background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius); box-shadow: 0 4px 16px rgba(0,0,0,.08); padding: 4px; display: grid; }
.exportMenu button { text-align: left; border: 0; background: transparent; padding: 7px 10px; font-size: 13px; color: var(--text-2); border-radius: var(--radius); }
.exportMenu button:hover { background: var(--hover); }
</style>
