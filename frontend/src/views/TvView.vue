<script setup>
// A dashboard on a TV (D18): no sign-in, dark, full screen. It loops over the dashboard's screens
// (one every `rotate_seconds`) and fetches new numbers every `refresh_seconds`; both come with
// the board, so editing the dashboard changes the TV at its next fetch.
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
const index = ref(0)
// Bumped whenever a screen's time starts again: it restarts the progress bar's animation.
const cycle = ref(0)

const screens = computed(() => board.value?.screens || [])
const current = computed(() => screens.value[index.value] || null)

let fetchTimer
let rotateTimer
async function load() {
  clearTimeout(fetchTimer)
  try {
    board.value = await tvBoard(route.params.token)
    stale.value = false
    if (index.value >= screens.value.length) index.value = 0
    scheduleRotate()
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) { gone.value = true; board.value = null; return }
    stale.value = true   // keep showing the last numbers; try again at the next tick
  }
  fetchTimer = setTimeout(load, (board.value?.refresh_seconds || 60) * 1000)
}

// The rotation restarts only when its interval changes, so a fetch doesn't reset the screen's time.
let rotateEvery = 0
function scheduleRotate() {
  const s = board.value?.rotate_seconds || 30
  if (s === rotateEvery && rotateTimer) return
  rotateEvery = s
  clearInterval(rotateTimer)
  cycle.value++
  rotateTimer = setInterval(() => {
    if (screens.value.length > 1) index.value = (index.value + 1) % screens.value.length
    cycle.value++
  }, s * 1000)
}

// Rows of three columns, from the charts' widths: everything fits on one screen.
const rows = computed(() => {
  const cols = (current.value?.charts || []).reduce((a, c) => a + (c.width || 1), 0)
  return Math.min(4, Math.max(1, Math.ceil(cols / 3)))
})

onMounted(() => {
  document.documentElement.classList.add('tvMode')
  load()
})
onUnmounted(() => {
  clearTimeout(fetchTimer)
  clearInterval(rotateTimer)
  document.documentElement.classList.remove('tvMode')
})
</script>

<template>
  <div class="tv">
    <p v-if="gone" class="gone">{{ t('dash.tvGone') }}</p>
    <template v-else-if="board">
      <header class="tvHead">
        <div class="tvTitle">
          <h1>{{ board.name }}</h1>
          <span v-if="current?.title" class="screenTitle">{{ current.title }}</span>
        </div>
        <div class="tvRight">
          <span v-if="screens.length > 1" class="dots" :aria-label="t('dash.screenOf', { n: index + 1, total: screens.length })">
            <i v-for="(s, i) in screens" :key="i" :class="{ on: i === index }"></i>
          </span>
          <span class="when" :class="{ stale }">{{ t('dash.tvUpdated', { time: fmtTime(board.generated_at) }) }}</span>
        </div>
      </header>
      <div v-if="current" :key="index" class="tvGrid" :style="{ gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))` }">
        <section v-for="(c, i) in current.charts" :key="i" class="tile" :class="`w${c.width}`">
          <DashChart :result="c.result" :error="c.error" dark big fill />
        </section>
      </div>
      <!-- How long until the next screen: a thin line along the bottom that fills up. -->
      <div v-if="screens.length > 1" class="progress" aria-hidden="true">
        <i :key="cycle" :style="{ animationDuration: `${board.rotate_seconds}s` }"></i>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tv { position: fixed; inset: 0; background: #0b121a; color: #e6edf3; padding: 28px 36px; display: flex; flex-direction: column; overflow: hidden; }
.tvHead { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 22px; }
.tvHead h1 { margin: 0; font-weight: 300; font-size: 30px; letter-spacing: -.01em; }
.tvTitle { display: flex; align-items: baseline; min-width: 0; }
.screenTitle { color: #8a9bb0; margin-left: 18px; font-size: 24px; font-weight: 300; }
.screenTitle::before { content: '·'; margin-right: 18px; }
.tvRight { display: flex; align-items: center; gap: 24px; }
.dots { display: inline-flex; gap: 8px; }
.dots i { width: 8px; height: 8px; border-radius: 50%; background: #2a3a4c; }
.dots i.on { background: #8b85ff; }
.when { color: #8a9bb0; font-size: 16px; font-variant-numeric: tabular-nums; }
.when.stale { color: #f0a14a; }
.tvGrid { flex: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; min-height: 0; animation: fadeIn .4s ease; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.tile { display: flex; flex-direction: column; min-height: 0; background: #0f1822; border: 1px solid #1c2836; border-radius: 6px; padding: 20px 24px; min-width: 0; overflow: hidden; }
.w2 { grid-column: span 2; }
.w3 { grid-column: span 3; }
.tile > :deep(.dchart) { flex: 1; min-height: 0; }
.progress { position: absolute; left: 0; right: 0; bottom: 0; height: 3px; background: #131d29; }
.progress i { display: block; height: 100%; width: 100%; background: #8b85ff; opacity: .55;
  transform-origin: left; transform: scaleX(0); animation: fillUp linear forwards; }
@keyframes fillUp { to { transform: scaleX(1); } }
.gone { margin: auto; color: #8a9bb0; font-size: 22px; font-weight: 300; }
</style>
