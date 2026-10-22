<script setup>
// Report template choice, shown as a single chip (like the operator chips): it reads
// "Nenhum" or the chosen template's name; clicking it opens the list of templates.
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { t } from '../i18n'

const props = defineProps({
  modelValue: { type: String, default: null },   // template id, or null for none
  templates: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const root = ref(null)

// Unshared templates are available to nobody (admins see them on the Templates page only).
const usable = computed(() => props.templates.filter((x) => x.can_use))
const chosen = computed(() => usable.value.find((tpl) => tpl.id === props.modelValue) || null)
// Mine first, then the ones shared with everyone, then (admins only) other users' ones.
const groups = computed(() => [
  { key: 'mine', items: usable.value.filter((x) => x.mine) },
  { key: 'global', items: usable.value.filter((x) => !x.mine && x.is_global) },
  { key: 'others', items: usable.value.filter((x) => !x.mine && !x.is_global) },
].filter((g) => g.items.length))

function pick(id) {
  emit('update:modelValue', id)
  open.value = false
}

const onDoc = (e) => { if (open.value && root.value && !root.value.contains(e.target)) open.value = false }
onMounted(() => document.addEventListener('click', onDoc))
onUnmounted(() => document.removeEventListener('click', onDoc))
</script>

<template>
  <div ref="root" class="tplPicker">
    <button type="button" class="opchip" :class="{ on: !!chosen }" @click.stop="open = !open">
      {{ chosen ? chosen.name : t('tpl.none') }}
    </button>
    <div v-if="open" class="tplMenu">
      <button type="button" class="tplItem" :class="{ current: !modelValue }" @click="pick(null)">{{ t('tpl.none') }}</button>
      <template v-for="g in groups" :key="g.key">
        <div class="tplGroup">{{ t('tpl.group.' + g.key) }}</div>
        <button v-for="x in g.items" :key="x.id" type="button" class="tplItem"
                :class="{ current: x.id === modelValue }" @click="pick(x.id)">
          <span class="tplName">{{ x.name }}</span>
          <span v-if="g.key === 'others'" class="tplOwner">{{ x.owner.username }}</span>
          <span v-else-if="g.key === 'mine' && x.share_status !== 'private'" class="tplOwner">{{ t('tpls.status.' + x.share_status) }}</span>
        </button>
      </template>
      <p v-if="!usable.length" class="tplEmpty">{{ t('tpl.empty') }}</p>
    </div>
  </div>
</template>

<style scoped>
.tplPicker { position: relative; display: inline-block; }
.opchip { border: 1px solid var(--line-2); background: var(--panel); color: var(--text-2); border-radius: var(--radius); padding: 4px 12px; font-size: 13px; }
.opchip:hover:not(.on) { background: var(--hover); }
.opchip.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.tplMenu { position: absolute; top: calc(100% + 4px); left: 0; z-index: 20; min-width: 260px; max-width: 360px; max-height: 320px; overflow-y: auto; background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--radius); box-shadow: 0 4px 16px rgba(0,0,0,.08); padding: 6px; display: grid; }
.tplGroup { font-size: 11px; color: var(--muted); padding: 8px 8px 4px; text-transform: uppercase; letter-spacing: .04em; }
.tplItem { display: flex; justify-content: space-between; gap: 12px; text-align: left; border: 0; background: transparent; padding: 6px 8px; font-size: 13px; color: var(--text-2); border-radius: var(--radius); }
.tplItem:hover { background: var(--hover); }
.tplItem.current { color: var(--accent); }
.tplName { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tplOwner { color: var(--muted); font-size: 12px; flex: 0 0 auto; }
.tplEmpty { margin: 4px 8px 6px; font-size: 12px; color: var(--muted); }
</style>
