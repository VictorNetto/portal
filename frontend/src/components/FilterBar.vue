<script setup>
import { ref, computed, nextTick } from 'vue'
import { FILTER_KEYS } from '../filterQuery'

const props = defineProps({
  modelValue: String,
  // Dynamic value sets for enumerable keys whose values aren't static,
  // e.g. { operator: ['alice', 'bob'] }. Resolved by the parent from data.
  dynamicValues: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const activeIdx = ref(0)
const dismissed = ref(false) // set by Escape; cleared on next input

const text = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const hasText = computed(() => (text.value || '').length > 0)

const KEY_LIST = FILTER_KEYS.map((k) => k.key)
const KEY_DESC = Object.fromEntries(FILTER_KEYS.map((k) => [k.key, k.desc]))
const KEY_DEF = Object.fromEntries(FILTER_KEYS.map((k) => [k.key, k]))

function valuesFor(key) {
  const def = KEY_DEF[key]
  if (!def || !def.enumerable) return null
  // Prefer a dynamic set (e.g. operators from loaded rows) when provided.
  if (props.dynamicValues[key]?.length) return props.dynamicValues[key]
  return def.values
}

// Follows the SecTools model: the menu is derived from the CURRENT term (last
// whitespace-delimited chunk). Two modes:
//   key mode   — term is "/..." or "-/..."  -> list matching filter keys
//   value mode — term is "[-]key:partial" and key is enumerable -> list values
const term = computed(() => ((text.value || '').match(/(\S*)$/) || ['', ''])[1])

const autocomplete = computed(() => {
  if (dismissed.value) return null
  const t = term.value

  // key mode
  const negate = t[0] === '-' && t[1] === '/'
  const slashIndex = negate ? 1 : t[0] === '/' ? 0 : -1
  if (slashIndex !== -1) {
    const needle = t.slice(slashIndex + 1).toLowerCase()
    const options = KEY_LIST.filter((k) => k.startsWith(needle))
    if (!options.length) return null
    return { mode: 'key', negate, options }
  }

  // value mode: "[-]key:partial" — show ALL of the key's values (no filtering
  // by the typed partial).
  const neg2 = t[0] === '-' && t.length > 1
  const body = neg2 ? t.slice(1) : t
  const colon = body.indexOf(':')
  if (colon > 0) {
    const key = body.slice(0, colon).toLowerCase()
    const vals = valuesFor(key)
    if (vals && vals.length) return { mode: 'value', negate: neg2, key, options: vals }
  }
  return null
})

function applyAutocomplete(choice) {
  const ac = autocomplete.value
  if (!ac) return
  const base = (text.value || '').replace(/\S*$/, '')
  if (ac.mode === 'key') {
    // after choosing a key, keep the menu open so its value menu can show
    text.value = base + (ac.negate ? '-' : '') + choice + ':'
    dismissed.value = false
  } else {
    // value mode: complete the token (no trailing space) and close the menu
    text.value = base + (ac.negate ? '-' : '') + ac.key + ':' + choice
    dismissed.value = true
  }
  activeIdx.value = 0
  nextTick(() => inputEl.value?.focus())
}

function onInput() {
  dismissed.value = false
  activeIdx.value = 0
}

function onKeydown(e) {
  const ac = autocomplete.value
  if (!ac) return
  const n = ac.options.length
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx.value = (activeIdx.value + 1) % n }
  else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx.value = (activeIdx.value - 1 + n) % n }
  else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); applyAutocomplete(ac.options[activeIdx.value]) }
  else if (e.key === 'Escape') { e.preventDefault(); dismissed.value = true }
}

function clearAll() {
  text.value = ''
  dismissed.value = false
  nextTick(() => inputEl.value?.focus())
}

// Parent calls this when the user presses "/" outside the input.
function focusAndTrigger() {
  inputEl.value?.focus()
  const cur = text.value || ''
  const needsSpace = cur.length && !cur.endsWith(' ')
  text.value = cur + (needsSpace ? ' /' : '/')
  dismissed.value = false
  activeIdx.value = 0
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
      @blur="() => setTimeout(() => (dismissed = true), 120)"
    />

    <!-- trailing adornment: ? (help) when empty, × (clear) when there's text -->
    <button v-if="hasText" class="adorn clear" @click="clearAll" title="Limpar filtro">×</button>
    <span v-else class="adorn help" tabindex="0">?
      <span class="tip">
        <strong>Filtro</strong>
        <span v-for="(line, i) in HELP_LINES" :key="i">{{ line }}</span>
      </span>
    </span>

    <!-- autocomplete menu: keys (term "/" or "-/") or values (term "key:…").
         Shows only the name — no description or key suffix. -->
    <ul v-if="autocomplete" class="menu">
      <li v-for="(opt, i) in autocomplete.options" :key="opt"
          :class="{ active: i === activeIdx }"
          @mousedown.prevent="applyAutocomplete(opt)">
        <span class="mono">{{ opt }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.filterbar { position: relative; display: flex; align-items: center; width: 100%; min-width: 180px; }
.field {
  flex: 1; background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius-sm);
  padding: .5rem 2rem .5rem .7rem; color: var(--text); font-size: .9rem; height: 36px;
}
.field::placeholder { color: var(--dim); }
.field:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

.adorn {
  position: absolute; right: 8px; width: 20px; height: 20px; border-radius: 50%;
  display: grid; place-items: center; font-size: .85rem; line-height: 1; border: 0;
}
.adorn.help {
  color: var(--muted); border: 1px solid var(--line-2); background: var(--panel); cursor: help;
}
.adorn.help:hover, .adorn.help:focus { color: var(--accent); border-color: var(--accent); outline: none; }
.adorn.clear {
  color: var(--muted); background: transparent; font-size: 1.1rem; cursor: pointer;
}
.adorn.clear:hover { color: var(--danger); }

/* Delayed tooltip for the ? help. */
.tip {
  position: absolute; top: 28px; right: 0; width: 300px; z-index: 70;
  display: flex; flex-direction: column; gap: 4px;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius-sm);
  box-shadow: var(--shadow-pop); padding: 10px 12px; color: var(--text-2); font-size: .78rem;
  opacity: 0; visibility: hidden; transition: opacity .12s ease; transition-delay: 0s;
  text-align: left; font-family: var(--sans);
}
.tip strong { color: var(--accent); font-size: .82rem; margin-bottom: 2px; }
.adorn.help:hover .tip, .adorn.help:focus .tip { opacity: 1; visibility: visible; transition-delay: .5s; }

.menu {
  position: absolute; top: 42px; left: 0; z-index: 60; margin: 0; padding: 6px; list-style: none;
  min-width: 160px; width: max-content; max-width: 420px;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius-sm); box-shadow: var(--shadow-pop);
  max-height: min(70vh, 460px); overflow: auto;
}
.menu li { display: flex; align-items: baseline; gap: 10px; padding: 7px 12px; border-radius: 6px; cursor: pointer; white-space: nowrap; }
.menu li.active, .menu li:hover { background: var(--hover); }
.menu li .mono { color: var(--accent); }
</style>
