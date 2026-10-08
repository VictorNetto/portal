<script setup>
// Operators of a vulnerability/report. Only the selected users are listed (plus the logged-in
// user, who stays visible even when unselected); "+" opens a small searchable list to add others.
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { t } from '../i18n'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: { type: Set, required: true },
  users: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const auth = useAuthStore()
const selfId = computed(() => auth.user?.id)
const open = ref(false)
const q = ref('')
const root = ref(null)

const shown = computed(() => props.users.filter((u) =>
  props.modelValue.has(u.id) || (!props.disabled && u.id === selfId.value)))
const addable = computed(() => {
  const needle = q.value.trim().toLowerCase()
  return props.users.filter((u) => !shown.value.some((s) => s.id === u.id)
    && (!needle || u.username.toLowerCase().includes(needle)))
})

function set(next) { emit('update:modelValue', new Set(next)) }
function toggle(id) {
  if (props.disabled) return
  const next = new Set(props.modelValue)
  if (next.has(id)) next.delete(id); else next.add(id)
  set(next)
}
function add(id) {
  set([...props.modelValue, id])
  open.value = false
  q.value = ''
}

const onDoc = (e) => { if (open.value && root.value && !root.value.contains(e.target)) open.value = false }
onMounted(() => document.addEventListener('click', onDoc))
onUnmounted(() => document.removeEventListener('click', onDoc))
</script>

<template>
  <div ref="root" class="opchips" :class="{ locked: disabled }">
    <button v-for="u in shown" :key="u.id" type="button" class="opchip"
            :class="{ on: modelValue.has(u.id) }" :disabled="disabled" @click="toggle(u.id)">
      {{ u.username }}
    </button>
    <span v-if="!shown.length" class="muted">{{ t('vform.noOperators') }}</span>
    <div v-if="!disabled" class="opadd">
      <button type="button" class="opchip plus" :aria-label="t('vform.addOperator')" @click.stop="open = !open">+</button>
      <div v-if="open" class="oppop">
        <input v-model="q" class="opsearch" :placeholder="t('vform.searchUser')" autofocus />
        <div class="oplist">
          <button v-for="u in addable" :key="u.id" type="button" class="opitem" @click="add(u.id)">{{ u.username }}</button>
          <span v-if="!addable.length" class="muted opempty">{{ t('vform.noOtherUsers') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.opchips { display: flex; flex-wrap: wrap; gap: 8px; min-height: 32px; align-items: center; }
.opchip { border: 1px solid var(--line-2); background: var(--panel); color: var(--text-2); border-radius: var(--radius); padding: 4px 12px; font-size: 13px; }
.opchip:hover:not(:disabled):not(.on) { background: var(--hover); }
.opchip.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.opchip:disabled { cursor: default; opacity: .7; }
.opchip.plus { padding: 4px 10px; }
.opadd { position: relative; }
.oppop { position: absolute; top: calc(100% + 4px); left: 0; z-index: 20; width: 220px; background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius); box-shadow: 0 4px 16px rgba(0,0,0,.08); padding: 8px; display: grid; gap: 6px; }
.opsearch { width: 100%; box-sizing: border-box; }
.oplist { max-height: 200px; overflow-y: auto; display: grid; }
.opitem { text-align: left; border: 0; background: transparent; padding: 6px 8px; font-size: 13px; color: var(--text-2); border-radius: var(--radius); }
.opitem:hover { background: var(--hover); }
.opempty { padding: 6px 8px; font-size: 12px; }
</style>
