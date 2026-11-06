<script setup>
// CVSS v3.1 calculator (base metrics), laid out like FIRST's: one row per metric, a button per
// value. The score, severity and vector follow every choice; "Aplicar" hands both back.
import { computed, ref } from 'vue'
import { METRICS, baseScore, parseVector, severity, toVector } from '../cvss'
import { t } from '../i18n'

const props = defineProps({ vector: { type: String, default: '' } })
const emit = defineEmits(['apply', 'close'])

// Starts from the vector already on the form, so reopening it edits what is there.
const chosen = ref(parseVector(props.vector))
const score = computed(() => baseScore(chosen.value))
const level = computed(() => severity(score.value))
const vector = computed(() => toVector(chosen.value))
const missing = computed(() => METRICS.filter(({ key }) => !chosen.value[key]).length)

const EXPLOITABILITY = METRICS.filter(({ key }) => ['AV', 'AC', 'PR', 'UI'].includes(key))
const IMPACT = METRICS.filter(({ key }) => ['S', 'C', 'I', 'A'].includes(key))

function pick(key, value) { chosen.value = { ...chosen.value, [key]: value } }
function apply() { if (score.value != null) emit('apply', { score: score.value, vector: vector.value }) }
</script>

<template>
  <div class="modalBack" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section class="panel modal calc" role="dialog" aria-modal="true" :aria-label="t('cvssCalc.title')">
      <h2 class="secTitle">{{ t('cvssCalc.title') }}</h2>

      <div class="cols">
        <div v-for="(group, gi) in [EXPLOITABILITY, IMPACT]" :key="gi" class="col">
          <div class="groupTitle">{{ t(gi === 0 ? 'cvssCalc.exploitability' : 'cvssCalc.impact') }}</div>
          <div v-for="m in group" :key="m.key" class="metric">
            <div class="mName">{{ t(`cvssCalc.m.${m.key}.name`) }} <span class="mKey">({{ m.key }})</span></div>
            <div class="opts" role="radiogroup" :aria-label="t(`cvssCalc.m.${m.key}.name`)">
              <button v-for="v in m.values" :key="v" type="button" class="opt" role="radio"
                      :class="{ on: chosen[m.key] === v }" :aria-checked="chosen[m.key] === v"
                      @click="pick(m.key, v)">
                {{ t(`cvssCalc.m.${m.key}.${v}`) }} <span class="mKey">({{ v }})</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="result">
        <div class="scoreBox" :class="level">
          <span class="score mono">{{ score == null ? '—' : score.toFixed(1) }}</span>
          <span class="sev">{{ level ? t(`cvssCalc.sev.${level}`) : t('cvssCalc.missing', { n: missing }) }}</span>
        </div>
        <div class="vec mono">{{ vector || 'CVSS:3.1/…' }}</div>
      </div>

      <div class="modalActions">
        <button type="button" class="btn" @click="emit('close')">{{ t('dialog.cancel') }}</button>
        <button type="button" class="btn primary" :disabled="score == null" @click="apply">{{ t('cvssCalc.apply') }}</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.calc { width: min(880px, 100%); max-height: calc(100vh - 32px); overflow: auto; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 32px; }
.groupTitle { font-size: 12px; color: var(--muted); margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
.metric { margin: 10px 0 14px; }
.mName { font-size: 13px; color: var(--text); margin-bottom: 6px; }
.mKey { color: var(--dim); font-family: var(--mono); font-size: 11px; }
.opts { display: flex; flex-wrap: wrap; gap: 6px; }
.opt {
  height: 30px; padding: 0 10px; border: 1px solid var(--line-2); border-radius: var(--radius);
  background: var(--panel); color: var(--text-2); font-size: 13px;
}
.opt:hover:not(.on) { background: var(--hover); }
.opt.on { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
.opt.on .mKey { color: var(--accent); }

.result { display: flex; align-items: center; gap: 18px; padding-top: 12px; border-top: 1px solid var(--line); }
.scoreBox { display: flex; align-items: baseline; gap: 10px; flex: 0 0 auto; }
.score { font-size: 26px; font-weight: 300; color: var(--text); }
.sev { font-size: 13px; color: var(--muted); }
.scoreBox.critical .score, .scoreBox.critical .sev, .scoreBox.high .score, .scoreBox.high .sev { color: var(--sev-hi); }
.scoreBox.medium .score, .scoreBox.medium .sev { color: var(--sev-me); }
.scoreBox.low .score, .scoreBox.low .sev { color: var(--sev-lo); }
.vec { font-size: 12px; color: var(--text-2); word-break: break-all; }

@media (max-width: 760px) { .cols { grid-template-columns: 1fr; } .result { flex-wrap: wrap; } }
</style>
