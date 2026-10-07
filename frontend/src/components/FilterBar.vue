<script setup>
import { ref, computed, nextTick } from 'vue'
import { FILTER_KEYS } from '../filterQuery'

const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const menuOpen = ref(false)
const activeIdx = ref(0)
const menuNegate = ref(false) // set when the menu was opened via "-/"

const text = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const hasText = computed(() => (text.value || '').length > 0)

// The menu always lists all keys; its contents do NOT depend on live text, so
// it renders reliably the moment it is opened.
const suggestions = computed(() => {
  const neg = menuNegate.value ? '-' : ''
  return FILTER_KEYS.map((k) => ({
    label: `${k.key}:`,
    desc: k.desc,
    insert: `${neg}${k.key}:`,
  }))
})

function openMenu(negate) {
  menuNegate.value = negate
  activeIdx.value = 0
  menuOpen.value = true
}

function applySuggestion(s) {
  // Replace the trailing "/" or "-/" fragment with the chosen "key:".
  const base = (text.value || '').replace(/[-]?\/?$/, '')
  text.value = base + s.insert
  menuOpen.value = false
  activeIdx.value = 0
  nextTick(() => inputEl.value?.focus())
}

function onInput() {
  // Close the menu once the user types past the "/" trigger.
  const frag = ((text.value || '').match(/(\S*)$/) || ['', ''])[1]
  if (frag !== '/' && frag !== '-/') menuOpen.value = false
}

function onKeydown(e) {
  if (menuOpen.value) {
    const list = suggestions.value
    if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx.value = (activeIdx.value + 1) % list.length; return }
    if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx.value = (activeIdx.value - 1 + list.length) % list.length; return }
    if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); applySuggestion(list[activeIdx.value]); return }
    if (e.key === 'Escape') { e.preventDefault(); menuOpen.value = false; return }
  }
  // "/" opens the key menu when at a token boundary (start, after a space, or
  // after a leading "-" for negation).
  if (e.key === '/') {
    const cur = text.value || ''
    const frag = (cur.match(/(\S*)$/) || ['', ''])[1]
    if (frag === '') openMenu(false)
    else if (frag === '-') openMenu(true)
  }
}

function clearAll() {
  text.value = ''
  nextTick(() => inputEl.value?.focus())
}

// Parent calls this when the user presses "/" outside the input: focus the bar
// and inject "/" so the key menu appears.
function focusAndTrigger() {
  inputEl.value?.focus()
  const cur = text.value || ''
  const needsSpace = cur.length && !cur.endsWith(' ')
  text.value = cur + (needsSpace ? ' /' : '/')
  nextTick(() => openMenu(false))
}
defineExpose({ focusAndTrigger })

const HELP_LINES = [
  'Digite / para ver as chaves de filtro.',
  'status:draft — status exato',
  'cvss:7 — CVSS maior ou igual a 7 (0–10, 1 casa decimal)',
  'id:CVE — identificador contém',
  'source:nuclei — fonte contém',
  'texto — busca livre no identificador',
  '-chave:valor — negação (exclui)',
  'Vários termos são combinados com E (AND).',
]
</script>

<template>
  <div class="filterbar">
    <input
      ref="inputEl"
      v-model="text"
      class="mono field"
      placeholder="Filtrar"
      @input="onInput"
      @keydown="onKeydown"
      @blur="() => setTimeout(() => (menuOpen = false), 120)"
    />

    <!-- trailing adornment: ? (help) when empty, × (clear) when there's text -->
    <button v-if="hasText" class="adorn clear" @click="clearAll" title="Limpar filtro">×</button>
    <span v-else class="adorn help" tabindex="0">?
      <span class="tip">
        <strong>Filtro</strong>
        <span v-for="(line, i) in HELP_LINES" :key="i">{{ line }}</span>
      </span>
    </span>

    <!-- key suggestion menu (only on "/" or "-/") -->
    <ul v-if="menuOpen && suggestions.length" class="menu">
      <li v-for="(s, i) in suggestions" :key="s.insert"
          :class="{ active: i === activeIdx }"
          @mousedown.prevent="applySuggestion(s)">
        <span class="mono">{{ s.label }}</span>
        <em>{{ s.desc }}</em>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.filterbar { position: relative; display: flex; align-items: center; min-width: 320px; }
.field {
  flex: 1; background: #0b0f14; border: 1px solid var(--line); border-radius: 6px;
  padding: .5rem 2rem .5rem .6rem; color: var(--text); font-size: .9rem;
}
.field:focus { outline: none; border-color: var(--green); }

.adorn {
  position: absolute; right: 8px; width: 20px; height: 20px; border-radius: 50%;
  display: grid; place-items: center; font-size: .85rem; line-height: 1; border: 0;
}
.adorn.help {
  color: var(--muted); border: 1px solid var(--line2); background: transparent; cursor: help;
}
.adorn.help:hover, .adorn.help:focus { color: var(--green); border-color: var(--green); outline: none; }
.adorn.clear {
  color: var(--muted); background: transparent; font-size: 1.1rem; cursor: pointer;
}
.adorn.clear:hover { color: var(--red); }

/* Delayed tooltip for the ? help. */
.tip {
  position: absolute; top: 28px; right: 0; width: 300px; z-index: 70;
  display: flex; flex-direction: column; gap: 4px;
  background: #071211; border: 1px solid rgba(66, 230, 123, .4); border-radius: 8px;
  box-shadow: var(--shadow); padding: 10px 12px; color: var(--text); font-size: .78rem;
  opacity: 0; visibility: hidden; transition: opacity .12s ease; transition-delay: 0s;
  text-align: left; font-family: var(--sans);
}
.tip strong { color: var(--green); font-size: .82rem; margin-bottom: 2px; }
.adorn.help:hover .tip, .adorn.help:focus .tip { opacity: 1; visibility: visible; transition-delay: .5s; }

.menu {
  position: absolute; top: 42px; left: 0; right: 0; z-index: 60; margin: 0; padding: 6px; list-style: none;
  background: #071211; border: 1px solid rgba(66, 230, 123, .4); border-radius: 8px; box-shadow: var(--shadow);
  max-height: 260px; overflow: auto;
}
.menu li { display: flex; align-items: baseline; gap: 10px; padding: 7px 10px; border-radius: 6px; cursor: pointer; }
.menu li.active, .menu li:hover { background: rgba(66, 230, 123, .12); }
.menu li .mono { color: var(--green); }
.menu li em { color: var(--muted); font-style: normal; font-size: .76rem; }
</style>
