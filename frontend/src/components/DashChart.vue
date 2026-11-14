<script setup>
// One chart of a dashboard (D18), drawn as SVG from a result of the API
// (backend/app/services/dashboard_engine.py). `dark` and `big` are for the TV board.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { t } from '../i18n'
import { bucketLabel, colorOf, errorText, fmtValue, groupLabel, measureLabel } from '../dashboards'

const props = defineProps({
  result: { type: Object, default: null },
  error: { type: Object, default: null },
  dark: { type: Boolean, default: false },
  big: { type: Boolean, default: false },
  height: { type: Number, default: 220 },
  // Fill the parent's height (the TV tiles) instead of `height`.
  fill: { type: Boolean, default: false },
})

const box = ref(null)
const width = ref(480)
const boxH = ref(0)
let ro
onMounted(() => {
  ro = new ResizeObserver(([e]) => {
    width.value = Math.max(200, Math.floor(e.contentRect.width))
    boxH.value = Math.floor(e.contentRect.height)
  })
  if (box.value) ro.observe(box.value)
})
onBeforeUnmount(() => ro?.disconnect())

const r = computed(() => props.result)
const fs = computed(() => (props.big ? 15 : 11))           // axis and label text
const title = computed(() => r.value?.title || (r.value ? measureLabel(r.value) : ''))

// Dimensions: with over, by[0] names the series; without, by[0] is the x axis, by[1] the series.
const xDim = computed(() => (r.value?.over ? null : r.value?.by?.[0]))
const sDim = computed(() => (r.value?.over ? r.value?.by?.[0] : r.value?.by?.[1]))
const xLabels = computed(() => (r.value?.x || []).map((x) =>
  r.value.over ? bucketLabel(x.key, r.value.over.unit, true) : groupLabel(xDim.value, x)))
const xFull = computed(() => (r.value?.x || []).map((x) =>
  r.value.over ? bucketLabel(x.key, r.value.over.unit) : groupLabel(xDim.value, x)))
const series = computed(() => (r.value?.series || []).map((s, i) => ({
  key: s.key, label: groupLabel(sDim.value, s), color: colorOf(sDim.value, s.key, i, props.dark),
})))
const single = computed(() => !series.value.length)
// A single series grouped by severity or status keeps those colors on each bar.
const barColor = (xi, si) => (single.value
  ? colorOf(xDim.value, r.value.x[xi].key, null, props.dark)
  : series.value[si].color)

const values = computed(() => r.value?.values || [])
const stackTotals = computed(() => values.value.map((row) => row.reduce((a, v) => a + (v || 0), 0)))
const empty = computed(() => r.value && r.value.chart !== 'number' && !(r.value.x || []).length)

const isStack = computed(() => r.value?.measure === 'count')   // durations don't add up
const top = computed(() => Math.max(0, ...(isStack.value ? stackTotals.value : values.value.flat().map((v) => v ?? 0))))
// About 4 grid steps of 1, 2 or 5 × 10^k; counts never get a fractional step.
const step = computed(() => {
  const raw = Math.max(top.value, 1) / 4
  const p = 10 ** Math.floor(Math.log10(raw))
  const n = raw / p
  const s = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p
  return isStack.value ? Math.max(1, Math.round(s)) : s
})
const maxV = computed(() => Math.max(step.value, Math.ceil(top.value / step.value) * step.value))
const ticks = computed(() => Array.from({ length: Math.round(maxV.value / step.value) + 1 }, (_, i) => i * step.value))
const fmtTick = (v) => (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(1))
// The plot's height: given, or what the parent leaves after the title and the legend.
const plotHeight = computed(() => (props.fill && boxH.value
  ? Math.max(140, boxH.value - (props.big ? 50 : 34) - (series.value.length > 1 ? (props.big ? 44 : 32) : 0))
  : props.height))

// --- vertical bars and lines -----------------------------------------------------------
const M = computed(() => ({ l: props.big ? 44 : 34, r: 10, t: 8, b: props.big ? 30 : 24 }))
const plotW = computed(() => width.value - M.value.l - M.value.r)
const plotH = computed(() => plotHeight.value - M.value.t - M.value.b)
const band = computed(() => plotW.value / Math.max(1, values.value.length))
const y = (v) => M.value.t + plotH.value * (1 - (v || 0) / maxV.value)
// Show at most as many x labels as fit.
const labelEvery = computed(() => {
  const room = Math.max(1, Math.floor(plotW.value / (fs.value * 4.2)))
  return Math.max(1, Math.ceil(values.value.length / room))
})

const columns = computed(() => {
  const out = []
  const groups = Math.max(1, series.value.length)
  values.value.forEach((row, xi) => {
    const x0 = M.value.l + xi * band.value
    if (isStack.value || single.value) {
      const w = Math.min(band.value * 0.62, props.big ? 70 : 48)
      let acc = 0
      row.forEach((v, si) => {
        if (!v) return
        out.push({ x: x0 + (band.value - w) / 2, w, y: y(acc + v), h: y(acc) - y(acc + v), fill: barColor(xi, si),
                   tip: `${xFull.value[xi]}${single.value ? '' : ' · ' + series.value[si].label}: ${fmtValue(v, r.value)}` })
        acc += v
      })
    } else {  // durations by series: side by side
      const w = Math.min((band.value * 0.7) / groups, 26)
      const start = x0 + (band.value - w * groups) / 2
      row.forEach((v, si) => {
        if (v === null) return
        out.push({ x: start + si * w, w: w - 1, y: y(v), h: y(0) - y(v), fill: barColor(xi, si),
                   tip: `${xFull.value[xi]} · ${series.value[si].label}: ${fmtValue(v, r.value)}` })
      })
    }
  })
  return out
})
// Totals above single-series bars, when they fit.
const colTotals = computed(() => {
  if (!single.value || band.value < fs.value * 2.2) return []
  return values.value.map((row, xi) => ({
    x: M.value.l + (xi + 0.5) * band.value, y: y(row[0]) - 5, text: fmtValue(row[0], r.value), show: row[0] !== null,
  })).filter((c) => c.show && (values.value.length <= 16))
})

const lines = computed(() => {
  const n = values.value.length
  const cx = (i) => M.value.l + (i + 0.5) * band.value
  const ss = single.value ? [{ key: null, label: '', color: colorOf(null, null, null, props.dark) }] : series.value
  return ss.map((s, si) => {
    let d = ''
    let pen = false
    const pts = []
    for (let i = 0; i < n; i++) {
      const v = values.value[i][si]
      if (v === null || v === undefined) { pen = false; continue }
      d += `${pen ? 'L' : 'M'}${cx(i).toFixed(1)},${y(v).toFixed(1)}`
      pen = true
      pts.push({ x: cx(i), y: y(v), tip: `${xFull.value[i]}${s.label ? ' · ' + s.label : ''}: ${fmtValue(v, r.value)}` })
    }
    return { d, color: s.color, pts }
  })
})

// --- horizontal bars -------------------------------------------------------------------
const hb = computed(() => {
  const rows = values.value.length
  const rowH = props.big ? 34 : 24
  const labelW = Math.min(Math.max(...xLabels.value.map((l) => l.length), 4) * fs.value * 0.56 + 8, width.value * 0.42)
  const valW = fs.value * 3.4
  const barW = width.value - labelW - valW - 6
  const bars = []
  values.value.forEach((row, xi) => {
    let acc = 0
    row.forEach((v, si) => {
      if (!v) return
      const w = (barW * v) / maxV.value
      bars.push({ x: labelW + (barW * acc) / maxV.value, y: xi * rowH + rowH * 0.18, w, h: rowH * 0.64,
                  fill: barColor(xi, si),
                  tip: `${xFull.value[xi]}${single.value ? '' : ' · ' + series.value[si].label}: ${fmtValue(v, r.value)}` })
      acc += v
    })
  })
  const totals = values.value.map((row, xi) => ({
    x: labelW + (barW * (isStack.value ? stackTotals.value[xi] : row[0] || 0)) / maxV.value + 6,
    y: xi * rowH + rowH / 2,
    text: isStack.value ? fmtValue(stackTotals.value[xi], r.value) : fmtValue(row[0], r.value),
  }))
  return { rowH, labelW, bars, totals, h: rows * rowH + 4 }
})

// --- table -----------------------------------------------------------------------------
const table = computed(() => {
  const res = r.value
  const cols = single.value ? [measureLabel(res)] : series.value.map((s) => s.label)
  const withTotal = res.measure === 'count' && !single.value
  const withN = res.measure !== 'count'
  const rows = values.value.map((row, xi) => ({
    label: xFull.value[xi],
    cells: row.map((v) => fmtValue(v, res)),
    total: withTotal ? fmtValue(stackTotals.value[xi], res) : null,
    n: withN ? res.sizes[xi].reduce((a, b) => a + b, 0) : null,
  }))
  const head = res.over ? '' : t(`dash.dims.${xDim.value}`)
  return { head, cols, rows, withTotal, withN }
})
</script>

<template>
  <div ref="box" class="dchart" :class="{ dark, big, fill }">
    <div class="dtitle">{{ title }}</div>
    <p v-if="error" class="derr">{{ errorText(error) }}</p>
    <template v-else-if="r">
      <!-- a single number -->
      <div v-if="r.chart === 'number'" class="dnum">
        <span class="dval">{{ fmtValue(r.value, r) }}</span>
        <span v-if="r.measure !== 'count'" class="dsub">{{ t('dash.days') }} · {{ t('dash.n') }} {{ r.n }}</span>
      </div>

      <p v-else-if="empty" class="dempty">{{ t('dash.nothing') }}</p>

      <!-- a table -->
      <div v-else-if="r.chart === 'table'" class="dtableWrap">
        <table class="dtable">
          <thead><tr>
            <th>{{ table.head }}</th>
            <th v-for="c in table.cols" :key="c" class="num">{{ c }}</th>
            <th v-if="table.withTotal" class="num">Total</th>
            <th v-if="table.withN" class="num">{{ t('dash.n') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="row in table.rows" :key="row.label">
              <td>{{ row.label }}</td>
              <td v-for="(c, i) in row.cells" :key="i" class="num">{{ c }}</td>
              <td v-if="table.withTotal" class="num strong">{{ row.total }}</td>
              <td v-if="table.withN" class="num muted">{{ row.n }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- horizontal bars -->
      <svg v-else-if="r.chart === 'hbar'" :width="width" :height="hb.h" class="dsvg" role="img" :aria-label="title">
        <g v-for="(l, i) in xLabels" :key="'l' + i">
          <text :x="hb.labelW - 8" :y="i * hb.rowH + hb.rowH / 2" text-anchor="end" dominant-baseline="central"
                class="tlabel" :font-size="fs">{{ l.length > 34 ? l.slice(0, 33) + '…' : l }}<title>{{ xFull[i] }}</title></text>
        </g>
        <rect v-for="(b, i) in hb.bars" :key="'b' + i" :x="b.x" :y="b.y" :width="Math.max(1, b.w - 1)" :height="b.h"
              :fill="b.fill" rx="2"><title>{{ b.tip }}</title></rect>
        <text v-for="(tt, i) in hb.totals" :key="'t' + i" :x="tt.x" :y="tt.y" dominant-baseline="central"
              class="tval" :font-size="fs">{{ tt.text }}</text>
      </svg>

      <!-- columns and lines -->
      <svg v-else :width="width" :height="plotHeight" class="dsvg" role="img" :aria-label="title">
        <g v-for="tk in ticks" :key="tk">
          <line :x1="M.l" :x2="width - M.r" :y1="y(tk)" :y2="y(tk)" class="grid" />
          <text :x="M.l - 6" :y="y(tk)" text-anchor="end" dominant-baseline="central" class="taxis" :font-size="fs - 1">{{ fmtTick(tk) }}</text>
        </g>
        <template v-if="r.chart === 'bar'">
          <rect v-for="(c, i) in columns" :key="i" :x="c.x" :y="c.y" :width="c.w" :height="Math.max(0, c.h)"
                :fill="c.fill" class="col"><title>{{ c.tip }}</title></rect>
          <text v-for="(c, i) in colTotals" :key="'v' + i" :x="c.x" :y="c.y" text-anchor="middle" class="tval" :font-size="fs">{{ c.text }}</text>
        </template>
        <template v-else>
          <g v-for="(l, li) in lines" :key="li">
            <path :d="l.d" :stroke="l.color" fill="none" :stroke-width="big ? 3 : 2" stroke-linejoin="round" stroke-linecap="round" />
            <circle v-for="(p, pi) in l.pts" :key="pi" :cx="p.x" :cy="p.y" :r="big ? 4 : 3" :fill="l.color" class="pt">
              <title>{{ p.tip }}</title></circle>
          </g>
        </template>
        <g v-for="(l, i) in xLabels" :key="'x' + i">
          <text v-if="i % labelEvery === 0" :x="M.l + (i + 0.5) * band" :y="plotHeight - M.b + fs + 4" text-anchor="middle"
                class="taxis" :font-size="fs - 1">{{ l.length > 14 ? l.slice(0, 13) + '…' : l }}<title>{{ xFull[i] }}</title></text>
        </g>
      </svg>

      <div v-if="series.length > 1 && r.chart !== 'table' && !empty" class="dlegend">
        <span v-for="s in series" :key="s.key" class="dkey"><i :style="{ background: s.color }"></i>{{ s.label }}</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dchart { --c-text: var(--text); --c-muted: var(--muted); --c-grid: var(--line); --c-bg: var(--panel);
  color: var(--c-text); min-width: 0; }
.dchart.dark { --c-text: #e6edf3; --c-muted: #8a9bb0; --c-grid: #223042; --c-bg: #0f1822; }
.dtitle { font-size: 13px; color: var(--c-text); margin-bottom: 10px; font-weight: 400; }
.big .dtitle { font-size: 20px; font-weight: 300; margin-bottom: 14px; }
.derr { color: var(--danger); font-size: 12px; margin: 0; }
.dark .derr { color: #ff8a8a; }
.dempty { color: var(--c-muted); font-size: 12px; margin: 20px 0; }
.dnum { display: flex; flex-direction: column; gap: 4px; padding: 6px 0 4px; }
.dval { font-size: 44px; font-weight: 300; line-height: 1; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.big .dval { font-size: 96px; }
.dsub { font-size: 12px; color: var(--c-muted); }
.big .dsub { font-size: 16px; }
.dsvg { display: block; overflow: visible; }
.fill { height: 100%; display: flex; flex-direction: column; }
.fill .dnum { flex: 1; justify-content: center; }
.fill.big .dval { font-size: clamp(96px, 14vh, 200px); }
.fill .dsvg { flex: 0 0 auto; }
.grid { stroke: var(--c-grid); stroke-width: 1; }
.taxis { fill: var(--c-muted); font-variant-numeric: tabular-nums; }
.tlabel { fill: var(--c-text); }
.tval { fill: var(--c-text); font-variant-numeric: tabular-nums; }
.col { stroke: var(--c-bg); stroke-width: 1; }
.pt { stroke: var(--c-bg); stroke-width: 1.5; }
.dlegend { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 10px; font-size: 12px; color: var(--c-muted); }
.big .dlegend { font-size: 15px; }
.dkey { display: inline-flex; align-items: center; gap: 6px; }
.dkey i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.dtableWrap { overflow-x: auto; }
.dtable { width: 100%; border-collapse: collapse; font-size: 12px; }
.big .dtable { font-size: 16px; }
.dtable th { text-align: left; font-weight: 400; color: var(--c-muted); padding: 4px 8px; border-bottom: 1px solid var(--c-grid); white-space: nowrap; }
.dtable td { padding: 5px 8px; border-bottom: 1px solid var(--c-grid); color: var(--c-text); }
.dtable .num { text-align: right; font-variant-numeric: tabular-nums; }
.dtable .strong { font-weight: 500; }
.dtable .muted { color: var(--c-muted); }
</style>
