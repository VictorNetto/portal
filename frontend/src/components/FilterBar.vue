<script setup>
import { ref, computed, nextTick } from 'vue'
import { parseQuery, FILTER_KEYS } from '../filterQuery'

const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const menuOpen = ref(false)
const activeIdx = ref(0)

const text = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const tokens = computed(() => parseQuery(text.value).tokens)
const hasText = computed(() => (text.value || '').length > 0)

// The fragment currently being typed (last whitespace-delimited chunk).
const currentFragment = computed(() => {
  const m = (text.value || '').match(/(\S*)$/)
  return m ? m[1] : ''
})

// Menu opens ONLY when the current fragment is "/" (keys) or "-/" (negated keys).
const triggerState = computed(() => {
  const f = currentFragment.value
  if (f === '/') return { show: true, negate: false }
  if (f === '-/') return { show: true, negate: true }
  return { show: false, negate: false }
})

const suggestions = computed(() => {
  if (!triggerState.value.show) return []
  const neg = triggerState.value.negate ? '-' : ''
  return FILTER_KEYS.map((k) => ({
    label: `${k.key}:`,
    desc: k.desc,
    insert: `${neg}${k.key}:`,
  }))
})

function maybeOpenMenu() {
  if (triggerState.value.show) {
    menuOpen.value = true
    activeIdx.value = 0
  } else {
    menuOpen.value = false
  }
}

function onInput() { maybeOpenMenu() }

function applySuggestion(s) {
  // Replace the trailing "/" or "-/" fragment with the chosen "key:".
  const base = (text.value || '').replace(/(\S*)$/, '')
  text.value = base + s.insert
  nextTick(() => {
    inputEl.value?.focus()
    menuOpen.value = false
    activeIdx.value = 0
  })
}

function onKeydown(e) {
  if (!menuOpen.value) return
  const list = suggestions.value
  if (!list.length) return
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx.value = (activeIdx.value + 1) % list.length }
  else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx.value = (activeIdx.value - 1 + list.length) % list.length }
  else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); applySuggestion(list[activeIdx.value]) }
  else if (e.key === 'Escape') { e.preventDefault(); menuOpen.value = false }
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
  nextTick(maybeOpenMenu)
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

    <!-- token validity chips -->
    <div v-if="tokens.length" class="chips">
      <span v-for="(tk, i) in tokens" :key="i" class="chip"
            :class="{ bad: !tk.valid, neg: tk.negate }"
            :title="tk.valid ? '' : 'inválido — ignorado'">{{ tk.raw }}</span>
    </div>

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

.chips { position: absolute; top: 42px; left: 2px; display: flex; gap: 6px; flex-wrap: wrap; pointer-events: none; z-index: 5; }
.chip { font-size: .72rem; border: 1px solid var(--line2); border-radius: 4px; padding: 1px 6px; background: rgba(66, 230, 123, .06); color: var(--text); }
.chip.neg { border-color: var(--amber); color: var(--amber); background: rgba(245, 167, 66, .07); }
.chip.bad { border-color: rgba(255, 107, 95, .6); color: var(--red); background: rgba(255, 107, 95, .07); text-decoration: line-through; }

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
