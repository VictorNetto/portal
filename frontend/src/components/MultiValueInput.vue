<script setup>
// Comma-separated values in a single field (e.g. several sources). Hovering the
// field (when it isn't focused) lists the individual values in a tooltip.
import { ref, computed, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const el = ref(null)
const tipVisible = ref(false)
let timer = null

const items = computed(() =>
  (props.modelValue || '').split(',').map((v) => v.trim()).filter(Boolean))

function showSoon() {
  if (document.activeElement === el.value || !items.value.length) return
  timer = setTimeout(() => { tipVisible.value = true }, 450)
}
function hide() {
  clearTimeout(timer)
  tipVisible.value = false
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="mv" @mouseenter="showSoon" @mouseleave="hide">
    <input ref="el" :value="modelValue" :placeholder="placeholder" :disabled="disabled"
           @input="emit('update:modelValue', $event.target.value)"
           @focus="hide" @blur="hide" @keydown.enter.prevent="el.blur()" />
    <div v-if="tipVisible" class="tip">
      <div v-for="v in items" :key="v">{{ v }}</div>
    </div>
  </div>
</template>

<style scoped>
.mv { position: relative; }
.mv input { width: 100%; }
.tip {
  position: absolute; left: 0; top: calc(100% + 6px); z-index: 50; min-width: 220px; max-width: 420px;
  padding: 8px 12px; background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  box-shadow: var(--shadow-pop); font-family: var(--mono); font-size: 12px; line-height: 1.6;
  pointer-events: none;
}
</style>
