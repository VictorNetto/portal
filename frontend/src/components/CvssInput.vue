<script setup>
// CVSS score input, ported from the prototype's behavior:
//  - at rest it shows the real score (0.0 - 10.0);
//  - while focused it shows a 0 - 100 integer scale (type "75" for 7.5), so a
//    score can be typed without a decimal point;
//  - the mouse wheel steps by 0.1 at rest and by 1 (=0.1 real) while focused.
// The model value is always a number (0 - 10, one decimal) or null.
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [Number, String], default: null },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const el = ref(null)
const focused = ref(false)

const show = (v) => (v === null || v === '' || v === undefined ? '' : Number(v).toFixed(1))
const text = ref(show(props.modelValue))

watch(() => props.modelValue, (v) => { if (!focused.value) text.value = show(v) })

function clean(value) {
  const normalized = String(value).replace(',', '.').replace(/[^0-9.]/g, '')
  const parts = normalized.split('.')
  return parts.length > 1 ? `${parts[0]}.${parts.slice(1).join('')}` : parts[0]
}

// "7.5" (decimal, <= 10) and "75" both mean 7.5: returns the 0-100 scale.
function toScaled(value) {
  const c = clean(value)
  if (c === '') return null
  const parsed = Number.parseFloat(c)
  if (Number.isNaN(parsed)) return null
  if (c.includes('.') && parsed <= 10) return Math.max(0, Math.min(100, Math.round(parsed * 10)))
  return Math.max(0, Math.min(100, Math.round(parsed)))
}
const toReal = (value) => {
  const s = toScaled(value)
  return s === null ? null : s / 10
}

function onFocus() {
  focused.value = true
  const s = toScaled(text.value)
  text.value = s === null ? '' : String(s)
  el.value?.select()
}
function onBlur() {
  focused.value = false
  const real = toReal(text.value)
  text.value = real === null ? '' : real.toFixed(1)
  emit('update:modelValue', real)
}
function onInput() {
  text.value = clean(text.value).slice(0, 3)
}
function onWheel(e) {
  if (props.disabled) return
  e.preventDefault()
  if (focused.value) {
    const s = toScaled(text.value) ?? 0
    text.value = String(Math.max(0, Math.min(100, s + (e.deltaY < 0 ? 1 : -1))))
    return
  }
  const real = toReal(text.value) ?? 0
  const next = Math.max(0, Math.min(10, Math.round((real + (e.deltaY < 0 ? 0.1 : -0.1)) * 10) / 10))
  text.value = next.toFixed(1)
  emit('update:modelValue', next)
}
function onEnter(e) {
  e.preventDefault()
  el.value?.blur()
}
</script>

<template>
  <input ref="el" v-model="text" class="cvss" :class="{ invalid }" inputmode="decimal"
         autocomplete="off" placeholder="0.0" :disabled="disabled"
         @focus="onFocus" @blur="onBlur" @input="onInput" @wheel="onWheel" @keydown.enter="onEnter" />
</template>

<style scoped>
.cvss { width: 100%; font-family: var(--mono); }
.cvss.invalid { border-color: var(--danger); }
</style>
