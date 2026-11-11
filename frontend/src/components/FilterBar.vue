<script setup>
import { ref, computed, nextTick } from 'vue'
import { FILTER_KEYS } from '../filterQuery'
import { t } from '../i18n'

const props = defineProps({
  modelValue: String,
  // Dynamic value sets for enumerable keys whose values aren't static,
  // e.g. { operator: ['alice', 'bob'] }. Resolved by the parent from data.
  dynamicValues: { type: Object, default: () => ({}) },
  keys: { type: Array, default: () => FILTER_KEYS },
  // i18n key of the help lines (an array).
  help: { type: String, default: 'filter.help' },
})
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const activeIdx = ref(0)
const dismissed = ref(false) // set by Escape; cleared on next input
// "/" lists the basic keys and MORE; choosing MORE lists every key.
const MORE = '\u0000more'
const expanded = ref(false)

const text = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const hasText = computed(() => (text.value || '').length > 0)

const KEY_LIST = computed(() => props.keys.map((k) => k.key))
const BASIC_KEYS = computed(() => props.keys.filter((k) => !k.advanced).map((k) => k.key))
const FIRST_ADVANCED = computed(() => props.keys.find((k) => k.advanced)?.key)
const KEY_DEF = computed(() => Object.fromEntries(props.keys.map((k) => [k.key, k])))

function valuesFor(key) {
  const def = KEY_DEF.value[key]
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
    // Just "/": the basic keys, and "more filters" when there are others. Typing a
    // name searches them all.
    if (!needle && !expanded.value && BASIC_KEYS.value.length < KEY_LIST.value.length) {
      return { mode: 'key', negate, options: [...BASIC_KEYS.value, MORE] }
    }
    const options = KEY_LIST.value.filter((k) => k.startsWith(needle))
    if (!options.length) return null
    return { mode: 'key', negate, options }
  }

  // value mode: "[-]key:partial". Nothing typed yet: all of the key's values. Once
  // something is typed, only the values that start with it; and no menu when none
  // does, or when it is already one of them, so Enter never swaps a typed value
  // (created:45d, cvss:7.5) for a suggestion.
  const neg2 = t[0] === '-' && t.length > 1
  const body = neg2 ? t.slice(1) : t
  const colon = body.indexOf(':')
  if (colon > 0) {
    const key = body.slice(0, colon).toLowerCase()
    const partial = body.slice(colon + 1).toLowerCase()
    const vals = valuesFor(key)
    if (!vals?.length) return null
    const options = partial ? vals.filter((v) => String(v).toLowerCase().startsWith(partial)) : vals
    if (!options.length || options.some((v) => String(v).toLowerCase() === partial)) return null
    return { mode: 'value', negate: neg2, key, options }
  }
  return null
})

function applyAutocomplete(choice) {
  const ac = autocomplete.value
  if (!ac) return
  if (choice === MORE) {
    expanded.value = true
    activeIdx.value = BASIC_KEYS.value.length // the first advanced key
    nextTick(() => inputEl.value?.focus())
    return
  }
  const base = (text.value || '').replace(/\S*$/, '')
  expanded.value = false
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

// Close the menu shortly after blur so a click on a menu item still registers.
function onBlur() {
  setTimeout(() => { dismissed.value = true; expanded.value = false }, 120)
}

function onInput() {
  dismissed.value = false
  activeIdx.value = 0
  if (!term.value.includes('/')) expanded.value = false
}

function onKeydown(e) {
  const ac = autocomplete.value
  if (!ac) return
  const n = ac.options.length
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx.value = (activeIdx.value + 1) % n }
  else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx.value = (activeIdx.value - 1 + n) % n }
  else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); applyAutocomplete(ac.options[activeIdx.value]) }
  else if (e.key === 'Escape') { e.preventDefault(); dismissed.value = true; expanded.value = false }
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
  expanded.value = false
  activeIdx.value = 0
}
defineExpose({ focusAndTrigger })

// Computed so the help follows the selected language.
const HELP_LINES = computed(() => t(props.help))
</script>

<template>
  <div class="filterbar">
    <input
      ref="inputEl"
      v-model="text"
      class="mono field"
      :placeholder="t('filter.placeholder')"
      @input="onInput"
      @keydown="onKeydown"
      @blur="onBlur"
    />

    <!-- trailing adornment: ? (help) when empty, × (clear) when there's text -->
    <button v-if="hasText" class="adorn clear" @click="clearAll">{{ t('common.clear') }}</button>
    <span v-else class="adorn help" tabindex="0">{{ t('common.help') }}
      <span class="tip">
        <strong>{{ t('filter.title') }}</strong>
        <span v-for="(line, i) in HELP_LINES" :key="i">{{ line }}</span>
      </span>
    </span>

    <!-- autocomplete menu: keys (term "/" or "-/") or values (term "key:…").
         Shows only the name — no description or key suffix. -->
    <ul v-if="autocomplete" class="menu">
      <li v-for="(opt, i) in autocomplete.options" :key="opt"
          :class="{ active: i === activeIdx, more: opt === MORE,
                    group: autocomplete.mode === 'key' && i > 0 && (opt === MORE || opt === FIRST_ADVANCED) }"
          @mousedown.prevent="applyAutocomplete(opt)">
        <span v-if="opt === MORE">{{ t('filter.more') }}</span>
        <span v-else class="mono">{{ opt }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.filterbar { position: relative; display: flex; align-items: center; width: 100%; min-width: 180px; }
.field { flex: 1; height: 32px; padding: 0 64px 0 10px; font-size: 13px; }
.adorn {
  position: absolute; right: 10px; border: 0; background: transparent; padding: 0;
  font-size: 12px; color: var(--muted); display: inline-flex; align-items: center;
}
.adorn.help { cursor: help; }
.adorn.help:hover, .adorn.help:focus { color: var(--text); outline: none; }
.adorn.clear:hover { color: var(--text); }

/* Delayed tooltip for the help text. */
.tip {
  position: absolute; top: 24px; right: 0; width: 300px; z-index: 70;
  display: flex; flex-direction: column; gap: 4px;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  box-shadow: var(--shadow-pop); padding: 10px 12px; color: var(--text-2); font-size: 12px;
  opacity: 0; visibility: hidden; transition: opacity .12s ease; transition-delay: 0s;
  text-align: left; font-family: var(--sans);
}
.tip strong { font-weight: 500; font-size: 12px; margin-bottom: 2px; }
.adorn.help:hover .tip, .adorn.help:focus .tip { opacity: 1; visibility: visible; transition-delay: .5s; }

.menu {
  position: absolute; top: 38px; left: 0; z-index: 60; margin: 0; padding: 4px; list-style: none;
  min-width: 160px; width: max-content; max-width: 420px;
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-pop);
  max-height: min(70vh, 460px); overflow: auto;
}
.menu li { display: flex; align-items: baseline; gap: 10px; padding: 6px 12px; border-radius: var(--radius-sm); cursor: pointer; white-space: nowrap; }
.menu li.active, .menu li:hover { background: var(--hover); }
.menu li .mono { color: var(--text-2); }
/* A hairline above "more filters", and above the first advanced key once they show. */
.menu li.group { margin-top: 5px; position: relative; }
.menu li.group::before { content: ''; position: absolute; left: 8px; right: 8px; top: -3px; border-top: 1px solid var(--line); }
.menu li.more { color: var(--muted); font-size: 13px; }
</style>
