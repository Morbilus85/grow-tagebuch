<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js'
import { api } from '../api.js'
import { fmt, say } from '../util.js'
import ClimateStrip from '../components/ClimateStrip.vue'
import TentTabs from '../components/TentTabs.vue'
import { loadTents, setTent, tent } from '../tent.js'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler)

const runs = ref([])
const setups = ref([])
const setupId = computed(() => tent.id)
const route = useRoute()
const router = useRouter()
const shown = computed(() => runs.value.filter((r) => r.run.setup_id === setupId.value))
const setup = computed(() => setups.value.find((s) => s.id === setupId.value))
const live = ref(null)
const offset = ref(1)
const svp = (t) => 0.6108 * Math.exp(17.27 * t / (t + 237.3))
// Vorschau mit dem eingegebenen Wert, bevor gespeichert ist
const preview = computed(() => {
  const t = live.value?.temp, rh = live.value?.rh, o = Number(offset.value)
  if (t == null || rh == null || Number.isNaN(o)) return null
  return { leafTemp: t - o, vpd: svp(t - o) - svp(t) * rh / 100 }
})
const dirty = computed(() => setup.value && Number(offset.value) !== (setup.value.leaf_offset ?? 1))
const hours = ref(48)
const rows = ref([])
const canvas = ref(null)
let chart

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()

async function load() {
  if (route.query.zelt) { setTent(Number(route.query.zelt)); router.replace({ path: '/klima' }) }
  const [t, se] = await Promise.all([api.get('today'), api.get('setups'), loadTents()])
  runs.value = t.runs
  setups.value = se
  if (!setupId.value) return
  offset.value = setup.value?.leaf_offset ?? 1
  ;[rows.value, live.value] = await Promise.all([api.get(`climate/${setupId.value}?hours=${hours.value}`),
    api.get(`climate/${setupId.value}/live`).catch(() => null)])
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
    data: { labels, datasets: [ds('Temperatur °C', 'temp', css('--amber'), 'y'), ds('Luftfeuchte %', 'rh', css('--leaf'), 'y1'), ds('VPD Blatt kPa', 'vpd_leaf', css('--led'), 'y2'), { ...ds('VPD Luft kPa', 'vpd', css('--muted'), 'y2'), borderWidth: 1, borderDash: [4, 3] }] },
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
async function saveOffset() {
  try {
    await api.patch(`setups/${setupId.value}`, { leaf_offset: Number(offset.value) })
    say('Blatt-Differenz gespeichert')
    load()
  } catch (e) { say(e.message) }
}
function setRange(h) { hours.value = h; load() }
const pct = computed(() => setup.value?.light_unit === 'prozent')
const hasHeat = (c) => c.heater_on !== null || c.heatmat_on !== null
const hasRoom = (c) => c.room_temp !== null || c.room_rh !== null
onMounted(load)
onUnmounted(() => chart?.destroy())
</script>

<template>
  <main class="page stack-lg">
    <TentTabs @change="load" />
    <div class="row between">
      <h1>Klima</h1>
      <router-link v-if="setupId" class="btn ghost" :to="{ path: '/ki/neu', query: { zelt: setupId } }">KI fragen</router-link>
    </div>
    <p v-if="!shown.length" class="small muted">Kein aktiver Durchgang in diesem Zelt – Zielbereiche erst mit Pflanzen.</p>
    <template v-for="r in shown" :key="r.run.id">
      <p v-if="shown.length > 1" class="small muted">{{ r.run.name }}</p>
      <ClimateStrip :climate="r.climate" :light="r.light" :setup-id="r.run.setup_id" :run-id="r.run.id" />
      <div class="panel grid3 small">
        <div v-if="hasRoom(r.climate)"><p class="muted">Raum</p><p class="num">{{ fmt.n(r.climate.room_temp) }} °C, {{ fmt.n(r.climate.room_rh, 0) }} %</p></div>
        <div v-if="hasHeat(r.climate)"><p class="muted">Heizung / Heizmatte</p>
          <p>{{ r.climate.heater_on === null ? '–' : r.climate.heater_on ? 'an' : 'aus' }} / {{ r.climate.heatmat_on === null ? '–' : r.climate.heatmat_on ? 'an' : 'aus' }}</p></div>
        <div v-if="r.climate.water_temp !== null"><p class="muted">Wasser (Reservoir)</p><p class="num">{{ fmt.n(r.climate.water_temp) }} °C</p></div>
        <div><p class="muted">Abluft / Lampe</p>
          <p class="num" v-if="pct">{{ fmt.n(r.climate.exhaust_level, 0) }} % / {{ r.climate.light_on === false ? 'aus' : fmt.n(r.climate.light_level, 0) + ' %' }}</p>
          <p class="num" v-else>Stufe {{ fmt.n(r.climate.exhaust_level, 0) }} / {{ fmt.n(r.climate.light_level, 0) }}</p></div>
      </div>
    </template>

    <div v-if="setup" class="panel stack">
      <div class="row between"><strong>Blatt-VPD</strong>
        <span v-if="live?.vpd_air != null" class="small muted num">Luft {{ fmt.n(live.vpd_air, 2) }} · Blatt {{ fmt.n(live.vpd_leaf, 2) }} kPa</span></div>
      <label class="field"><span>Blatt kühler als Luft (°C)</span>
        <input type="number" inputmode="decimal" step="0.1" min="-5" max="10" v-model="offset" /></label>
      <p v-if="preview" class="small num">Blatt {{ fmt.n(preview.leafTemp) }} °C bei {{ fmt.n(live.temp) }} °C Luft → Blatt-VPD {{ fmt.n(preview.vpd, 2) }} kPa</p>
      <p class="small muted">Lufttemperatur minus Blatttemperatur. Unter LED meist 1–2 °C, mit IR-Thermometer an der Blattoberseite unter der Lampe messen.
        Negativ, wenn das Blatt wärmer ist. Gilt für Anzeige, Zielbereich, Klima-Alarm und KI. Der Sensor-VPD vom Controller ist Luft-VPD.</p>
      <button v-if="dirty" class="primary" @click="saveOffset">Speichern</button>
    </div>

    <div class="row" role="group" aria-label="Zeitraum">
      <button v-for="h in [24, 48, 168, 720]" :key="h" :class="{ primary: hours === h }" @click="setRange(h)">
        {{ h < 168 ? h + ' h' : h === 168 ? '7 Tage' : '30 Tage' }}
      </button>
    </div>
    <div class="panel" style="height:320px">
      <canvas ref="canvas" v-show="rows.length"></canvas>
      <p v-if="!rows.length" class="empty muted">Noch keine Aufzeichnung. Die App speichert alle 10 Minuten einen Messwert, sobald sie als Add-on läuft.</p>
    </div>
    <p class="small muted">VPD-Zielbereiche: Sämling 0,4–0,8, Wachstum 0,8–1,2, Blüte 1,0–1,5, Reife 1,2–1,6 kPa. Bewertet wird Blatt-VPD.</p>
  </main>
</template>
