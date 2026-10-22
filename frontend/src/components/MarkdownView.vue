<script setup>
// Read-only rendering of Markdown (same safe renderer as the editor's preview).
// Embedded attachments are fetched with the bearer token and swapped in.
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { renderMarkdown } from '../markdown'
import { attachmentObjectUrl } from '../api'
import { t } from '../i18n'

const props = defineProps({ source: { type: String, default: '' } })
const root = ref(null)
const html = computed(() => renderMarkdown(props.source))

async function resolveImages() {
  await nextTick()
  for (const img of root.value?.querySelectorAll('img[data-att]') || []) {
    try { img.src = await attachmentObjectUrl(img.dataset.att) }
    catch { img.alt = `${img.alt} (${t('md.imageMissing')})` }
  }
}
watch(html, resolveImages)
onMounted(resolveImages)
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- renderMarkdown escapes everything first -->
  <div ref="root" class="mdView" v-html="html"></div>
</template>

<style scoped>
.mdView { line-height: 1.6; color: var(--text-2); font-size: 13px; }
.mdView :deep(h1), .mdView :deep(h2), .mdView :deep(h3) { margin: 0 0 10px; font-weight: 400; line-height: 1.25; color: var(--text); }
.mdView :deep(h1) { font-size: 20px; } .mdView :deep(h2) { font-size: 17px; } .mdView :deep(h3) { font-size: 14px; }
.mdView :deep(p) { margin: 0 0 10px; }
.mdView :deep(ul), .mdView :deep(ol) { margin: 0 0 10px 20px; padding: 0; }
.mdView :deep(code) { font-family: var(--mono); font-size: 12px; background: var(--hover); border: 1px solid var(--line); border-radius: 3px; padding: 1px 5px; }
.mdView :deep(pre) { margin: 0 0 10px; padding: 10px 12px; background: var(--hover); border: 1px solid var(--line); border-radius: var(--radius); overflow: auto; }
.mdView :deep(pre code) { border: 0; padding: 0; background: transparent; }
.mdView :deep(blockquote) { margin: 0 0 10px; padding: 6px 12px; border-left: 3px solid var(--line-2); color: var(--muted); }
.mdView :deep(a) { color: var(--accent); }
.mdView :deep(img) { max-width: 100%; border: 1px solid var(--line); border-radius: var(--radius); }
</style>
