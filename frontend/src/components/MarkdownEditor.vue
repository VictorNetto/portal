<script setup>
// Markdown editor (FRONTEND_SPEC §10): edit / preview modes, a formatting
// toolbar, a line-number gutter that stays aligned with wrapped lines, and a
// height that grows with the content (up to 12 lines, then scrolls).
//
// Images: when `imageUploader` is provided, images can be pasted, dropped or
// picked; each is uploaded by the parent and inserted as ![name](url).
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { renderMarkdown, attachmentPath } from '../markdown'
import { attachmentObjectUrl } from '../api'
import { t } from '../i18n'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  // async (file: File) => { id, name } | null
  imageUploader: { type: Function, default: null },
})
const emit = defineEmits(['update:modelValue'])

const LINE_H = 22        // px, matches the CSS line-height
const V_PAD = 16         // textarea top + bottom padding
const H_PAD = 24         // textarea left + right padding
const MAX_VISIBLE = 12

const root = ref(null)
const textarea = ref(null)
const gutter = ref(null)
const measurer = ref(null)
const preview = ref(null)
const filePicker = ref(null)

const mode = ref('edit')
const height = ref(LINE_H * 3 + V_PAD)
const lineHeights = ref([LINE_H])
const scrolls = ref(false)
const busy = ref(false)

const readOnlyEdit = computed(() => props.disabled)

// --- Height + gutter ------------------------------------------------------
function sync() {
  const ta = textarea.value
  const m = measurer.value
  if (!ta || !m || mode.value !== 'edit') return
  const lines = (props.modelValue || '').split('\n')
  const count = lines.length
  const viewport = Math.min(count + 2, MAX_VISIBLE) * LINE_H + V_PAD
  height.value = viewport

  // Each logical line's rendered height (wrapped lines are taller), so the
  // gutter number stays aligned with the first row of its line.
  m.style.width = `${Math.max(ta.clientWidth - H_PAD, 1)}px`
  const heights = lines.map((line) => {
    m.textContent = line.length ? line : ' '
    return Math.max(LINE_H, Math.ceil(m.getBoundingClientRect().height))
  })
  lineHeights.value = heights
  const content = heights.reduce((a, b) => a + b, 0) + V_PAD
  scrolls.value = count >= MAX_VISIBLE - 1 || content > viewport
}

function syncGutterScroll() {
  if (gutter.value && textarea.value) gutter.value.scrollTop = textarea.value.scrollTop
}

function onInput(e) {
  emit('update:modelValue', e.target.value)
}

watch(() => props.modelValue, () => nextTick(sync))

let observer = null
onMounted(() => {
  sync()
  if (typeof ResizeObserver !== 'undefined' && root.value) {
    observer = new ResizeObserver(() => sync())
    observer.observe(root.value)
  }
})
onBeforeUnmount(() => observer?.disconnect())

// --- Modes ----------------------------------------------------------------
async function setMode(next) {
  mode.value = next
  await nextTick()
  if (next === 'edit') sync()
  else resolveImages()
}

// --- Preview --------------------------------------------------------------
const html = computed(() => renderMarkdown(props.modelValue))

// Embedded attachments are fetched with the bearer token and swapped in.
async function resolveImages() {
  await nextTick()
  const imgs = preview.value?.querySelectorAll('img[data-att]') || []
  for (const img of imgs) {
    try {
      img.src = await attachmentObjectUrl(img.dataset.att)
    } catch {
      img.alt = `${img.alt} (${t('md.imageMissing')})`
    }
  }
}
watch(html, () => { if (mode.value === 'preview') resolveImages() })

// --- Formatting -----------------------------------------------------------
const TOOLS = [
  { key: 'bold', label: 'B', title: 'md.bold', wrap: '**' },
  { key: 'italic', label: 'I', title: 'md.italic', wrap: '*' },
  { key: 'heading', label: 'H', title: 'md.heading', prefix: '# ' },
  { key: 'ul', label: 'md.list', title: 'md.list', prefix: '- ', text: true },
  { key: 'ol', label: 'md.numbered', title: 'md.numbered', prefix: '1. ', text: true },
  { key: 'code', label: 'md.code', title: 'md.code', wrap: '`', text: true },
  { key: 'link', label: 'md.link', title: 'md.link', link: true, text: true },
  { key: 'quote', label: 'md.quote', title: 'md.quote', prefix: '> ', text: true },
]

function insert(text, selectInserted = false) {
  const ta = textarea.value
  ta.focus()
  const start = ta.selectionStart
  const end = ta.selectionEnd
  ta.setRangeText(text, start, end, selectInserted ? 'select' : 'end')
  emit('update:modelValue', ta.value)
}

function applyTool(tool) {
  if (props.disabled || mode.value !== 'edit') return
  const ta = textarea.value
  ta.focus()
  const selected = ta.value.slice(ta.selectionStart, ta.selectionEnd) || t('md.sampleText')
  if (tool.wrap) insert(`${tool.wrap}${selected}${tool.wrap}`)
  else if (tool.prefix) insert(`${tool.prefix}${selected}`)
  else if (tool.link) insert(`[${selected}](https://)`)
}

// --- Images ---------------------------------------------------------------
async function handleImages(files) {
  if (!props.imageUploader || props.disabled) return
  const images = [...files].filter((f) => f.type.startsWith('image/'))
  if (!images.length) return
  busy.value = true
  try {
    for (const file of images) {
      const res = await props.imageUploader(file)
      if (res) insert(`![${res.name}](${attachmentPath(res.id)})`)
    }
  } finally {
    busy.value = false
  }
}

function pickImage() {
  if (!props.imageUploader) {
    insert(`![${t('md.sampleText')}](https://)`)
    return
  }
  filePicker.value?.click()
}
function onPicked(e) {
  handleImages(e.target.files)
  e.target.value = ''
}
function onPaste(e) {
  const files = e.clipboardData?.files
  if (files?.length && props.imageUploader) {
    e.preventDefault()
    handleImages(files)
  }
}
function onDrop(e) {
  const files = e.dataTransfer?.files
  if (!files?.length) return
  // Always swallow file drops: the browser would otherwise navigate to the file.
  e.preventDefault()
  handleImages(files)
}
</script>

<template>
  <div ref="root" class="mdEditor" :class="{ invalid, preview: mode === 'preview', disabled }">
    <div class="toolbar">
      <div class="modes">
        <button type="button" class="tool" :class="{ active: mode === 'edit' }" @click="setMode('edit')">
          {{ t('md.edit') }}
        </button>
        <button type="button" class="tool" :class="{ active: mode === 'preview' }" @click="setMode('preview')">
          {{ t('md.preview') }}
        </button>
      </div>
      <span class="sep"></span>
      <button v-for="tool in TOOLS" :key="tool.key" type="button" class="tool"
              :class="{ mono: !tool.text }" :disabled="disabled || mode !== 'edit'"
              :title="t(tool.title)" @click="applyTool(tool)">
        {{ tool.text ? t(tool.label) : tool.label }}
      </button>
      <button type="button" class="tool" :disabled="disabled || mode !== 'edit'" @click="pickImage">
        {{ busy ? t('md.uploading') : t('md.image') }}
      </button>
      <input ref="filePicker" type="file" accept="image/png,image/jpeg,image/gif,image/webp"
             multiple hidden @change="onPicked" />
    </div>

    <div v-show="mode === 'edit'" class="pane">
      <div ref="gutter" class="gutter" :style="{ height: height + 'px' }" aria-hidden="true">
        <div v-for="(h, i) in lineHeights" :key="i" class="ln" :style="{ height: h + 'px' }">{{ i + 1 }}</div>
      </div>
      <textarea ref="textarea" class="area" spellcheck="false" :value="modelValue"
                :readonly="readOnlyEdit" :style="{ height: height + 'px', overflowY: scrolls ? 'auto' : 'hidden' }"
                @input="onInput" @scroll="syncGutterScroll" @paste="onPaste"
                @dragover.prevent @drop="onDrop"></textarea>
      <div ref="measurer" class="measurer" aria-hidden="true"></div>
    </div>

    <div v-show="mode === 'preview'" ref="preview" class="previewPane" v-html="html"></div>
  </div>
</template>

<style scoped>
.mdEditor { border: 1px solid var(--line-2); border-radius: var(--radius); background: var(--panel); overflow: hidden; }
.mdEditor:focus-within { border-color: var(--accent); }
.mdEditor.invalid { border-color: var(--danger); }

.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; padding: 6px 8px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
.modes { display: inline-flex; gap: 4px; }
.sep { width: 1px; height: 18px; background: var(--line-2); margin: 0 6px; }
.tool {
  height: 26px; min-width: 28px; padding: 0 9px; border: 1px solid transparent; border-radius: var(--radius-sm);
  background: transparent; color: var(--text-2); font-size: 12px; font-weight: 400;
}
.tool.mono { font-family: var(--mono); font-weight: 500; }
.tool:hover:not(:disabled):not(.active) { background: var(--hover); border-color: var(--line-2); }
.tool.active { background: var(--accent-soft); color: var(--accent); }
.tool:disabled { opacity: .35; cursor: not-allowed; }

.pane { display: flex; position: relative; }
.gutter {
  flex: 0 0 44px; width: 44px; padding: 8px 0; overflow: hidden; user-select: none;
  border-right: 1px solid var(--line); background: var(--panel-2); color: var(--dim);
  font-family: var(--mono); font-size: 12px; line-height: 22px; text-align: center;
}
.ln { display: flex; align-items: flex-start; justify-content: center; min-height: 22px; }
.area, .measurer {
  font-family: var(--mono); font-size: 13px; line-height: 22px; font-weight: 300;
  white-space: pre-wrap; overflow-wrap: break-word; tab-size: 2;
}
.area {
  flex: 1; min-width: 0; width: 100%; resize: none; border: 0; outline: 0; border-radius: 0;
  background: transparent; padding: 8px 12px; color: var(--text);
}
.disabled .area { color: var(--muted); }
.measurer { position: absolute; left: -99999px; top: 0; visibility: hidden; padding: 0; border: 0; }

.previewPane { min-height: 60px; padding: 14px 18px; line-height: 1.6; color: var(--text-2); overflow: auto; }
.previewPane :deep(h1), .previewPane :deep(h2), .previewPane :deep(h3) { margin: 0 0 12px; font-weight: 400; line-height: 1.25; color: var(--text); }
.previewPane :deep(h1) { font-size: 22px; } .previewPane :deep(h2) { font-size: 18px; } .previewPane :deep(h3) { font-size: 15px; }
.previewPane :deep(p) { margin: 0 0 12px; }
.previewPane :deep(ul), .previewPane :deep(ol) { margin: 0 0 12px 20px; padding: 0; }
.previewPane :deep(code) { font-family: var(--mono); font-size: 12.5px; background: var(--hover); border: 1px solid var(--line); border-radius: 3px; padding: 1px 5px; }
.previewPane :deep(pre) { margin: 0 0 12px; padding: 10px 12px; background: var(--hover); border: 1px solid var(--line); border-radius: var(--radius); overflow: auto; }
.previewPane :deep(pre code) { border: 0; padding: 0; background: transparent; }
.previewPane :deep(blockquote) { margin: 0 0 12px; padding: 6px 12px; border-left: 3px solid var(--line-2); color: var(--muted); }
.previewPane :deep(a) { color: var(--accent); }
.previewPane :deep(img) { max-width: 100%; border: 1px solid var(--line); border-radius: var(--radius); }
</style>
