<script setup>
import { nextTick, ref, watch } from 'vue'
import { dialog, closeDialog } from '../dialog'
import { t } from '../i18n'

const value = ref('')
const input = ref(null)
const okBtn = ref(null)

watch(() => dialog.current, async (d) => {
  if (!d) return
  value.value = d.value ?? ''
  await nextTick()
  if (d.kind === 'prompt') { input.value?.focus(); input.value?.select() } else okBtn.value?.focus()
})

const ok = () => closeDialog(dialog.current.kind === 'prompt' ? value.value : true)
const cancel = () => closeDialog(dialog.current.kind === 'prompt' ? null : false)
</script>

<template>
  <div v-if="dialog.current" class="modalBack appDialog" @click.self="cancel" @keydown.esc="cancel">
    <section :key="dialog.current.id" class="panel modal" role="dialog" aria-modal="true" :aria-label="dialog.current.title || t('dialog.title')">
      <h2 v-if="dialog.current.title" class="secTitle">{{ dialog.current.title }}</h2>
      <p class="dMsg">{{ dialog.current.message }}</p>
      <input v-if="dialog.current.kind === 'prompt'" ref="input" v-model="value"
             :type="dialog.current.type || 'text'" @keydown.enter="ok" />
      <div class="modalActions">
        <button class="btn" @click="cancel">{{ dialog.current.cancel || t('dialog.cancel') }}</button>
        <button ref="okBtn" class="btn primary" :class="{ dangerOk: dialog.current.danger }" @click="ok">
          {{ dialog.current.ok || t('dialog.ok') }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.appDialog { z-index: 80; }
.dMsg { margin: 0; font-size: 14px; line-height: 1.5; color: var(--text); white-space: pre-line; }
.btn.primary.dangerOk { background: var(--danger); border-color: var(--danger); }
</style>
