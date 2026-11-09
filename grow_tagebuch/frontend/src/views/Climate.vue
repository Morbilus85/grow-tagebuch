<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js'
import { api } from '../api.js'
import { fmt } from '../util.js'
import ClimateStrip from '../components/ClimateStrip.vue'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler)

const runs = ref([])
const setups = ref([])
const setupId = ref(null)
const route = useRoute()
const router = useRouter()
// Zelte zum Umschalten: mit aktivem Durchgang oder verknüpften Sensoren
const tents = computed(() => setups.value.filter((s) => s.sensors.length || runs.value.some((r) => r.run.setup_id === s.id)))
const shown = computed(() => runs.value.filter((r) => r.run.setup_id === setupId.value))
const hours = ref(48)
const rows = ref([])
const canvas = ref(null)
let chart

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()

async function load() {
  const [t, se] = await Promise.all([api.get('today'), api.get('setups')])
  runs.value = t.runs
  setups.value = se
  setupId.value = setupId.value || Number(route.query.zelt) || t.runs[0]?.run.setup_id || se[0]?.id
  rows.value = await api.get(`climate/${setupId.value}?hours=${hours.value}`)
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
function pickTent(id) { setupId.value = id; router.replace({ path: '/klima', query: { zelt: id } }); load() }
onMounted(load)
onUnmounted(() => chart?.destroy())
</script>

<template>
  <main class="page stack-lg">
    <h1>Klima</h1>
    <div v-if="tents.length > 1" class="row" role="group" aria-label="Zelt">
      <button v-for="s in tents" :key="s.id" :class="{ primary: s.id === setupId }" @click="pickTent(s.id)">{{ s.name }}</button>
    </div>
    <p v-if="!shown.length" class="small muted">Kein aktiver Durchgang in diesem Zelt – Zielbereiche erst mit Pflanzen.</p>
    <template v-for="r in shown" :key="r.run.id">
      <p v-if="shown.length > 1" class="small muted">{{ r.run.name }}</p>
      <ClimateStrip :climate="r.climate" :light="r.light" :setup-id="r.run.setup_id" :run-id="r.run.id" />
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
