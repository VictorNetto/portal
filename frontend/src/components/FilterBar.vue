<script setup>
import { ref, computed, nextTick } from 'vue'
import { parseQuery, FILTER_KEYS, STATUSES } from '../filterQuery'

const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const menuOpen = ref(false)
const activeIdx = ref(0)

const text = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// Live token chips (for validity feedback under the bar).
const tokens = computed(() => parseQuery(text.value).tokens)

// The token fragment currently being typed (last whitespace-delimited chunk).
const currentFragment = computed(() => {
  const m = (text.value || '').match(/(\S*)$/)
  return m ? m[1] : ''
})

// Context-aware suggestions: before a ":" suggest keys; after "key:" suggest
// that key's values.
const suggestions = computed(() => {
  let frag = currentFragment.value
  const neg = frag.startsWith('-')
  if (neg) frag = frag.slice(1)

  const colon = frag.indexOf(':')
  if (colon === -1) {
    // suggesting keys
    const q = frag.toLowerCase()
    return FILTER_KEYS
      .filter((k) => k.key.startsWith(q))
      .map((k) => ({ label: `${k.key}:`, desc: k.desc, insert: `${neg ? '-' : ''}${k.key}:`, keep: true }))
  }
  // suggesting values for the typed key
  const key = frag.slice(0, colon).toLowerCase()
  const partial = frag.slice(colon + 1).toLowerCase()
  const def = FILTER_KEYS.find((k) => k.key === key || (key === 'identifier' && k.key === 'id'))
  if (!def || !def.values.length) return []
  return def.values
    .filter((v) => v.toLowerCase().startsWith(partial))
    .map((v) => ({ label: v, desc: '', insert: `${neg ? '-' : ''}${def.key}:${v}`, keep: false }))
})

function openMenu() {
  menuOpen.value = true
  activeIdx.value = 0
}

function onKeydownGlobal(e) {
  // handled by parent; kept for interface parity
}

function onInput() {
  menuOpen.value = true
  activeIdx.value = 0
}

function applySuggestion(s) {
  // Replace the current fragment with the suggestion's insert text.
  const base = (text.value || '').replace(/(\S*)$/, '')
  text.value = base + s.insert + (s.keep ? '' : ' ')
  nextTick(() => {
    inputEl.value?.focus()
    // keep menu open when we only completed a key (keep=true)
    menuOpen.value = s.keep
    activeIdx.value = 0
  })
}

function onKeydown(e) {
  if (!menuOpen.value && e.key === 'ArrowDown') { openMenu(); return }
  if (!menuOpen.value) return
  const list = suggestions.value
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx.value = (activeIdx.value + 1) % list.length }
  else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx.value = (activeIdx.value - 1 + list.length) % list.length }
  else if (e.key === 'Enter') {
    if (list.length) { e.preventDefault(); applySuggestion(list[activeIdx.value]) }
    else menuOpen.value = false
  }
  else if (e.key === 'Escape') { e.preventDefault(); menuOpen.value = false }
  else if (e.key === 'Tab' && list.length) { e.preventDefault(); applySuggestion(list[activeIdx.value]) }
}

// Exposed so the parent can focus + open the menu when the user presses "/".
function focusAndOpen() {
  inputEl.value?.focus()
  openMenu()
}
defineExpose({ focusAndOpen })
</script>

<template>
  <div class="filterbar">
    <span class="slashKey mono">/</span>
    <input
      ref="inputEl"
      v-model="text"
      class="mono"
      placeholder="filtrar: status:draft cvss:7 -source:nuclei …"
      @input="onInput"
      @keydown="onKeydown"
      @focus="openMenu"
      @blur="() => setTimeout(() => (menuOpen = false), 120)"
    />
    <button v-if="text" class="clear" @click="text = ''" title="Limpar">×</button>

    <!-- token validity chips -->
    <div v-if="tokens.length" class="chips">
      <span v-for="(tk, i) in tokens" :key="i" class="chip"
            :class="{ bad: !tk.valid, neg: tk.negate }"
            :title="tk.valid ? '' : 'inválido — ignorado'">{{ tk.raw }}</span>
    </div>

    <!-- suggestion menu -->
    <ul v-if="menuOpen && suggestions.length" class="menu">
      <li v-for="(s, i) in suggestions" :key="s.insert"
          :class="{ active: i === activeIdx }"
          @mousedown.prevent="applySuggestion(s)">
        <span class="mono">{{ s.label }}</span>
        <em v-if="s.desc">{{ s.desc }}</em>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.filterbar { position: relative; display: flex; align-items: center; gap: 8px; min-width: 360px; }
.slashKey { color: var(--green); border: 1px solid var(--line2); border-radius: 4px; padding: 0 6px; font-size: .8rem; }
input {
  flex: 1; background: #0b0f14; border: 1px solid var(--line); border-radius: 6px;
  padding: .5rem .6rem; color: var(--text); font-size: .9rem;
}
input:focus { outline: none; border-color: var(--green); }
.clear { border: 0; background: transparent; color: var(--muted); font-size: 1.1rem; cursor: pointer; }
.clear:hover { color: var(--red); }

.chips { position: absolute; top: 44px; left: 34px; display: flex; gap: 6px; flex-wrap: wrap; pointer-events: none; }
.chip { font-size: .72rem; border: 1px solid var(--line2); border-radius: 4px; padding: 1px 6px; background: rgba(66, 230, 123, .06); color: var(--text); }
.chip.neg { border-color: var(--amber); color: var(--amber); background: rgba(245, 167, 66, .07); }
.chip.bad { border-color: rgba(255, 107, 95, .6); color: var(--red); background: rgba(255, 107, 95, .07); text-decoration: line-through; }

.menu {
  position: absolute; top: 44px; left: 34px; right: 34px; z-index: 60; margin: 0; padding: 6px; list-style: none;
  background: #071211; border: 1px solid rgba(66, 230, 123, .4); border-radius: 8px; box-shadow: var(--shadow);
  max-height: 260px; overflow: auto;
}
.menu li { display: flex; align-items: baseline; gap: 10px; padding: 7px 10px; border-radius: 6px; cursor: pointer; }
.menu li.active, .menu li:hover { background: rgba(66, 230, 123, .12); }
.menu li .mono { color: var(--green); }
.menu li em { color: var(--muted); font-style: normal; font-size: .76rem; }
</style>
