<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js'
import { api } from '../api.js'
import { fmt } from '../util.js'
import ClimateStrip from '../components/ClimateStrip.vue'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler)

const runs = ref([])
const hours = ref(48)
const rows = ref([])
const canvas = ref(null)
let chart

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()

async function load() {
  const t = await api.get('today')
  runs.value = t.runs
  const setup = t.runs[0]?.run.setup_id || 1
  rows.value = await api.get(`climate/${setup}?hours=${hours.value}`)
  await nextTick()
  draw()
}
function draw() {
  if (!canvas.value) return
  chart?.destroy()
  const long = hours.value > 48
  const labels = rows.value.map((r) => long ? fmt.dt(r.ts) : fmt.time(r.ts))
  const ds = (label, key, color, axis) => ({
    label, data: rows.value.map((r) => r[key]), borderColor: color, backgroundColor: color, yAxisID: axis,
    borderWidth: 2, pointRadius: 0, tension: 0.25, spanGaps: true,
  })
  const grid = css('--line'), ink = css('--muted')
  chart = new Chart(canvas.value, {
    type: 'line',
    data: { labels, datasets: [ds('Temperatur °C', 'temp', css('--amber'), 'y'), ds('Luftfeuchte %', 'rh', css('--leaf'), 'y1'), ds('VPD kPa', 'vpd', css('--led'), 'y2')] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: ink, boxWidth: 12 } } },
      scales: {
        x: { ticks: { color: ink, maxTicksLimit: 6 }, grid: { color: grid } },
        y: { position: 'left', ticks: { color: css('--amber') }, grid: { color: grid } },
        y1: { position: 'right', min: 0, max: 100, ticks: { color: css('--leaf') }, grid: { display: false } },
        y2: { display: false, min: 0, max: 3 },
      },
    },
  })
}
function setRange(h) { hours.value = h; load() }
onMounted(load)
onUnmounted(() => chart?.destroy())
</script>

<template>
  <main class="page stack-lg">
    <h1>Klima</h1>
    <template v-for="r in runs" :key="r.run.id">
      <ClimateStrip :climate="r.climate" :light="r.light" />
      <div class="panel grid3 small">
        <div><p class="muted">Raum</p><p class="num">{{ fmt.n(r.climate.room_temp) }} °C, {{ fmt.n(r.climate.room_rh, 0) }} %</p></div>
        <div><p class="muted">Heizung / Heizmatte</p>
          <p>{{ r.climate.heater_on === null ? '–' : r.climate.heater_on ? 'an' : 'aus' }} / {{ r.climate.heatmat_on === null ? '–' : r.climate.heatmat_on ? 'an' : 'aus' }}</p></div>
        <div><p class="muted">Abluft / Lampe</p><p class="num">Stufe {{ fmt.n(r.climate.exhaust_level, 0) }} / {{ fmt.n(r.climate.light_level, 0) }}</p></div>
      </div>
    </template>

    <div class="row" role="group" aria-label="Zeitraum">
      <button v-for="h in [24, 48, 168, 720]" :key="h" :class="{ primary: hours === h }" @click="setRange(h)">
        {{ h < 168 ? h + ' h' : h === 168 ? '7 Tage' : '30 Tage' }}
      </button>
    </div>
    <div class="panel" style="height:320px">
      <canvas ref="canvas" v-show="rows.length"></canvas>
      <p v-if="!rows.length" class="empty muted">Noch keine Aufzeichnung. Die App speichert alle 10 Minuten einen Messwert, sobald sie als Add-on läuft.</p>
    </div>
    <p class="small muted">VPD-Zielbereiche: Sämling 0,4–0,8, Wachstum 0,8–1,2, Blüte 1,0–1,5, Reife 1,2–1,6 kPa. Blatt-VPD rechnet mit 1 °C kühlerem Blatt.</p>
  </main>
</template>
