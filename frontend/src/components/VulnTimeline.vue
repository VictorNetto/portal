<script setup>
// Lifecycle timeline of a vulnerability: when it was created, completed, sent,
// put in fixing (with its RVS id), and so on. Steps not yet reached stay dimmed.
// Works with both the list row (Hub panel) and the full record (detail page).
import { computed } from 'vue'
import { t } from '../i18n'
import { fmtDate, fmtTime, fmtDateTime } from '../dates'

const props = defineProps({
  vuln: { type: Object, required: true },
  // Tighter layout without the RVS sub-line and "last updated" footer, for
  // places that already show those elsewhere (the Hub details panel).
  compact: { type: Boolean, default: false },
})

// `status` is the vuln status that makes this step the "current" one.
const STEPS = [
  { key: 'created', at: 'created_at', status: 'draft' },
  { key: 'ready', at: 'ready_at', status: 'ready' },
  { key: 'sent', at: 'sent_at', status: 'sent' },
  { key: 'fixing', at: 'fixing_at', status: 'fixing' },
  { key: 'retesting', at: 'retesting_at', status: 'retesting' },
  { key: 'fixed', at: 'fixed_at', status: 'fixed' },
]

const steps = computed(() => STEPS.map((s) => {
  const at = props.vuln[s.at] || null
  const current = props.vuln.status === s.status
  const reached = current || !!at
  return { ...s, value: at, current, reached }
}))

// A connector is "done" when the step after it has been reached.
const lineDone = (i) => steps.value[i + 1]?.reached
</script>

<template>
  <div class="timeline" :class="{ compact }">
    <ol class="steps">
      <li v-for="(s, i) in steps" :key="s.key" class="step"
          :class="{ reached: s.reached, current: s.current }">
        <div class="track">
          <span class="dot"></span>
          <span v-if="i < steps.length - 1" class="line" :class="{ done: lineDone(i) }"></span>
        </div>
        <div class="label">{{ t('timeline.' + s.key) }}</div>
        <div v-if="s.value" class="when" :title="fmtDateTime(s.value)">
          {{ fmtDate(s.value) }}<span class="time">{{ fmtTime(s.value) }}</span>
        </div>
        <div v-else class="when none">—</div>
        <div v-if="!compact && s.key === 'fixing' && vuln.rvs_id" class="rvs mono">{{ vuln.rvs_id }}</div>
      </li>
    </ol>
    <div v-if="!compact && vuln.updated_at" class="updated">
      {{ t('timeline.updated') }} {{ fmtDateTime(vuln.updated_at) }}
    </div>
  </div>
</template>

<style scoped>
.steps { list-style: none; margin: 0; padding: 0; display: flex; }
.step { flex: 1 1 0; min-width: 0; padding-right: 8px; }

.track { display: flex; align-items: center; height: 12px; margin-bottom: 8px; }
.dot { flex: 0 0 auto; width: 10px; height: 10px; border-radius: 50%; border: 1px solid var(--line-2); background: var(--panel); }
.line { flex: 1 1 auto; height: 1px; margin: 0 6px; background: var(--line-2); }
.line.done { background: var(--accent); }
.step.reached .dot { background: var(--accent); border-color: var(--accent); }

.label { font-size: 12px; color: var(--dim); }
.step.reached .label { color: var(--muted); }
.step.current .label { color: var(--text); }
.when { margin-top: 2px; font-size: 12px; color: var(--text-2); font-variant-numeric: tabular-nums; }
.when .time { margin-left: 6px; color: var(--dim); }
.when.none { color: var(--dim); }
.rvs { margin-top: 3px; font-size: 12px; color: var(--accent); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.updated { margin-top: 10px; font-size: 12px; color: var(--dim); }

.compact .track { margin-bottom: 4px; }
.compact .when { margin-top: 0; }

@media (max-width: 900px) {
  .steps { flex-direction: column; gap: 10px; }
  .track { display: none; }
  .step { padding: 0 0 0 12px; border-left: 1px solid var(--line-2); }
  .step.reached { border-left-color: var(--accent); }
}
</style>
