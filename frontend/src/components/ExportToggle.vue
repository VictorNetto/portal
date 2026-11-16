<script setup>
// Is this section in the record's documents (Exportar and the report sent)? Editable: a small
// checkbox in the section's title row. Read-only: a muted note, only when it is left out.
import { t } from '../i18n'

defineProps({
  modelValue: { type: Boolean, default: true },   // true = in the documents
  editable: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <label v-if="editable" class="exportToggle" :class="{ off: !modelValue }" :title="t('doc.toggleHint')">
    <input type="checkbox" :checked="modelValue" @change="emit('update:modelValue', $event.target.checked)" />
    {{ t('doc.inDocument') }}
  </label>
  <span v-else-if="!modelValue" class="exportToggle off">{{ t('doc.notInDocument') }}</span>
</template>

<style scoped>
.exportToggle { display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto; font-size: 12px; color: var(--muted); cursor: pointer; user-select: none; white-space: nowrap; }
span.exportToggle { cursor: default; }
.exportToggle input { margin: 0; }
.exportToggle.off { color: var(--st-wait-fg, var(--muted)); }
</style>
