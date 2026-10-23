// Session helpers shared by the views and the SessionGuard (D12).
//
// - Unsaved work: pages with an editor register a "dirty" check, so that when
//   the session ends the guard can offer to sign in again instead of throwing
//   the edits away.
// - Activity: the last user action is kept in localStorage so every open tab
//   shares one idle clock (an idle tab must not end a session used elsewhere).

import { onMounted, onUnmounted } from 'vue'

const dirtyChecks = new Set()

// Call from a view's setup with a function returning true while there are unsaved edits.
export function useUnsaved(isDirty) {
  onMounted(() => dirtyChecks.add(isDirty))
  onUnmounted(() => dirtyChecks.delete(isDirty))
}
export const hasUnsaved = () => [...dirtyChecks].some((f) => f())

// Set while the session ends with edits the user chose to discard: leave guards
// (route + beforeunload) must not ask again.
let discarding = false
export const isDiscarding = () => discarding
export const setDiscarding = (v) => { discarding = v }

const ACTIVITY_KEY = 'rtp_activity'
const read = (k) => { try { return Number(localStorage.getItem(k)) || 0 } catch { return 0 } }
const write = (k, v) => { try { localStorage.setItem(k, String(v)) } catch { /* private mode */ } }

let lastLocal = 0
export function lastActivity() { return Math.max(lastLocal, read(ACTIVITY_KEY)) }
export function markActivity(now = Date.now()) {
  lastLocal = now
  // Throttled: a write every few seconds is plenty for a 15-minute window.
  if (now - read(ACTIVITY_KEY) > 5000) write(ACTIVITY_KEY, now)
}
export function resetActivity(now = Date.now()) { lastLocal = now; write(ACTIVITY_KEY, now) }
