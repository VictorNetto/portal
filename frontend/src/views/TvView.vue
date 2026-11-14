<script setup>
// A dashboard on a TV (D18): no sign-in, dark, full screen, refreshed every minute.
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ApiError, tvBoard } from '../api'
import { t } from '../i18n'
import { fmtTime } from '../dates'
import DashChart from '../components/DashChart.vue'

const route = useRoute()
const board = ref(null)
const gone = ref(false)
const stale = ref(false)

async function load() {
  try {
    board.value = await tvBoard(route.params.token)
    stale.value = false
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) { gone.value = true; board.value = null }
    else stale.value = true   // keep showing the last numbers; try again at the next tick
  }
}

// Rows of three columns, from the charts' widths: everything fits on one screen.
const rows = computed(() => {
  const cols = (board.value?.charts || []).reduce((a, c) => a + (c.width || 1), 0)
  return Math.min(4, Math.max(1, Math.ceil(cols / 3)))
})

let timer
onMounted(() => {
  document.documentElement.classList.add('tvMode')
  load()
  timer = setInterval(load, 60 * 1000)
})
onUnmounted(() => { clearInterval(timer); document.documentElement.classList.remove('tvMode') })
</script>

<template>
  <div class="tv">
    <p v-if="gone" class="gone">{{ t('dash.tvGone') }}</p>
    <template v-else-if="board">
      <header class="tvHead">
        <h1>{{ board.name }}</h1>
        <span class="when" :class="{ stale }">{{ t('dash.tvUpdated', { time: fmtTime(board.generated_at) }) }}</span>
      </header>
      <div class="tvGrid" :style="{ gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))` }">
        <section v-for="(c, i) in board.charts" :key="i" class="tile" :class="`w${c.width}`">
          <DashChart :result="c.result" :error="c.error" dark big fill />
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tv { position: fixed; inset: 0; background: #0b121a; color: #e6edf3; padding: 28px 36px; display: flex; flex-direction: column; overflow: hidden; }
.tvHead { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 22px; }
.tvHead h1 { margin: 0; font-weight: 300; font-size: 30px; letter-spacing: -.01em; }
.when { color: #8a9bb0; font-size: 16px; font-variant-numeric: tabular-nums; }
.when.stale { color: #f0a14a; }
.tvGrid { flex: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; min-height: 0; }
.tile { display: flex; flex-direction: column; min-height: 0; background: #0f1822; border: 1px solid #1c2836; border-radius: 6px; padding: 20px 24px; min-width: 0; overflow: hidden; }
.w2 { grid-column: span 2; }
.w3 { grid-column: span 3; }
.tile > :deep(.dchart) { flex: 1; min-height: 0; }
.gone { margin: auto; color: #8a9bb0; font-size: 22px; font-weight: 300; }
</style>
