<script setup>
// Drag-and-drop / picker upload area plus the list of attached files. The parent
// owns the data and the API calls; this component only renders and emits.
import { ref } from 'vue'
import { t } from '../i18n'

defineProps({
  attachments: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['upload', 'remove', 'download', 'copy-markdown'])

const picker = ref(null)
const over = ref(false)

function onPicked(e) {
  emit('upload', [...e.target.files])
  e.target.value = ''
}
function onDrop(e) {
  over.value = false
  emit('upload', [...e.dataTransfer.files])
}

function size(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div>
    <div v-if="!disabled" class="drop" :class="{ over, busy: uploading }"
         @click="picker.click()" @dragover.prevent="over = true" @dragleave="over = false"
         @drop.prevent="onDrop">
      <p class="lead">
        {{ uploading ? t('attach.uploading') : t('attach.dropHere') }}
        <span v-if="!uploading" class="accent">{{ t('attach.orClick') }}</span>
      </p>
      <small>{{ t('attach.limits') }}</small>
      <input ref="picker" type="file" multiple hidden
             accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.csv,.zip" @change="onPicked" />
    </div>
    <p v-else class="muted note">{{ t('attach.locked') }}</p>

    <p v-if="error" class="err">{{ error }}</p>

    <p class="count muted">{{ t('attach.attached') }} ({{ attachments.length }})</p>
    <p v-if="!attachments.length" class="muted">{{ t('attach.none') }}</p>

    <ul v-else class="list">
      <li v-for="a in attachments" :key="a.id" class="item">
        <div class="meta">
          <span class="name">{{ a.display_name || a.original_filename }}</span>
          <span class="sub mono">{{ a.original_filename }} · {{ size(a.size_bytes) }}</span>
        </div>
        <div class="acts">
          <button v-if="a.is_image" type="button" class="link" @click="emit('copy-markdown', a)">
            {{ t('attach.copyMd') }}
          </button>
          <button type="button" class="link" @click="emit('download', a)">{{ t('attach.download') }}</button>
          <button v-if="!disabled" type="button" class="link danger" @click="emit('remove', a)">
            {{ t('attach.remove') }}
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.drop {
  border: 1px dashed var(--line-2); border-radius: var(--radius); padding: 28px 16px; text-align: center;
  color: var(--muted); cursor: pointer;
}
.drop.over { background: var(--accent-soft); border-color: var(--accent); }
.drop.busy { opacity: .6; cursor: progress; }
.drop .lead { margin: 0 0 6px; font-size: 13px; }
.drop small { color: var(--dim); font-size: 12px; }
.accent { color: var(--accent); }
.note { margin: 0; font-size: 13px; }
.count { margin: 14px 0 6px; font-size: 12px; }
.list { list-style: none; margin: 0; padding: 0; }
.item { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 0; border-top: 1px solid var(--line); }
.meta { display: flex; flex-direction: column; min-width: 0; }
.name { font-size: 13px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub { font-size: 11px; color: var(--dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.acts { display: flex; flex: 0 0 auto; }
.link { margin-left: 14px; }
.err { color: var(--danger); font-size: 13px; margin: 10px 0 0; }
</style>
