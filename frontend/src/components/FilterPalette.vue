<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { parseQuery, FILTER_HELP } from '../filterQuery'

const props = defineProps({ open: Boolean, modelValue: String })
const emit = defineEmits(['update:modelValue', 'apply', 'close'])

const text = ref(props.modelValue || '')
const inputEl = ref(null)

watch(() => props.open, (o) => {
  if (o) {
    text.value = props.modelValue || ''
    nextTick(() => inputEl.value?.focus())
  }
})

const parsed = computed(() => parseQuery(text.value))

function apply() {
  emit('update:modelValue', text.value)
  emit('apply', text.value)
  emit('close')
}
function close() { emit('close') }
function fillExample(tok) {
  text.value = (text.value ? text.value.trimEnd() + ' ' : '') + tok
  inputEl.value?.focus()
}
</script>

<template>
  <div v-if="open" class="overlay" @click.self="close">
    <div class="palette" @keydown.enter.prevent="apply" @keydown.esc.prevent="close">
      <div class="prompt">
        <span class="slash mono">/</span>
        <input ref="inputEl" v-model="text" class="mono"
               placeholder="status:draft cvss:>7 id:CVE…" />
      </div>

      <div v-if="parsed.tokens.length" class="tokens">
        <span v-for="(tk, i) in parsed.tokens" :key="i"
              class="tok" :class="{ bad: !tk.valid }" :title="tk.valid ? '' : 'token inválido — ignorado'">
          {{ tk.raw }}
        </span>
      </div>

      <div class="help">
        <span class="helpTitle mono">Exemplos</span>
        <button v-for="h in FILTER_HELP" :key="h.token" class="chip mono" @click="fillExample(h.token)">
          {{ h.token }}<em>{{ h.desc }}</em>
        </button>
      </div>

      <div class="foot">
        <span class="hint mono">Enter aplica · Esc fecha</span>
        <button class="btn" @click="apply">Aplicar</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 60; background: rgba(2, 8, 7, .55);
  display: flex; justify-content: center; align-items: flex-start; padding-top: 14vh;
}
.palette {
  width: 560px; max-width: 92vw; background: #071211;
  border: 1px solid rgba(66, 230, 123, .4); border-radius: 10px;
  box-shadow: var(--shadow); padding: 16px;
}
.prompt { display: flex; align-items: center; gap: 10px; }
.slash { color: var(--green); font-size: 22px; }
.prompt input {
  flex: 1; background: #0b0f14; border: 1px solid var(--line); border-radius: 6px;
  padding: .6rem .7rem; color: var(--text); font-size: 1rem;
}
.prompt input:focus { outline: none; border-color: var(--green); }
.tokens { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.tok {
  border: 1px solid var(--line2); color: var(--text); border-radius: 5px;
  padding: 2px 8px; font-size: .8rem; background: rgba(66, 230, 123, .06);
}
.tok.bad { border-color: rgba(255, 107, 95, .6); color: var(--red); background: rgba(255, 107, 95, .07); text-decoration: line-through; }
.help { margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.helpTitle { color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; width: 100%; }
.chip {
  border: 1px solid var(--line); background: #0b0f14; border-radius: 6px;
  padding: 4px 8px; color: var(--text); font-size: .78rem; display: inline-flex; gap: 8px; align-items: center;
}
.chip:hover { border-color: var(--green); color: var(--green); }
.chip em { color: var(--muted); font-style: normal; font-size: .72rem; }
.foot { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; }
.hint { color: var(--muted); font-size: .76rem; }
.btn {
  border: 1px solid #4df587; background: linear-gradient(180deg, #48df7d, #2fbf68);
  color: #03120a; font-weight: 600; border-radius: 6px; height: 34px; padding: 0 18px;
}
</style>
