// Portal-styled replacements for window.confirm / window.prompt. Both return a
// Promise, so callers write `if (!(await confirmDialog(msg))) return`.
// One dialog shows at a time; later requests wait in line.

import { reactive } from 'vue'

export const dialog = reactive({ current: null })
const queue = []
let seq = 0

function open(spec) {
  return new Promise((resolve) => {
    queue.push({ ...spec, id: ++seq, resolve })
    if (!dialog.current) dialog.current = queue[0]
  })
}

export function closeDialog(result) {
  const d = queue.shift()
  dialog.current = queue[0] || null
  d?.resolve(result)
}

// opts: { title, ok, cancel, danger }
export const confirmDialog = (message, opts = {}) => open({ kind: 'confirm', message, ...opts })

// Resolves to the typed text, or null if cancelled. opts: { title, value, ok, type }
export const promptDialog = (message, opts = {}) => open({ kind: 'prompt', message, value: '', ...opts })
