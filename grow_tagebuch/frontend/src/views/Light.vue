<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt, rating, say } from '../util.js'

const t = ref(null)
const info = ref(null)
const form = ref({})
const cal = ref({ distance_cm: 45, level: 7, point: 'A', ppfd: null })
const run = computed(() => t.value?.runs[0])
const PH = { seedling: 'Sämling', veg: 'Wachstum', bloom: 'Blüte' }

async function load() {
  t.value = await api.get('today')
  const r = run.value
  if (!r) return
  form.value = { light_hours: r.run.light_hours, light_level: r.run.light_level, lamp_distance_cm: r.run.lamp_distance_cm }
  info.value = await api.get(`light/${r.run.setup_id}?hours=${r.run.light_hours}`)
}
async function save() {
  await api.patch(`runs/${run.value.run.id}`, form.value)
  await api.post('logs', { run_id: run.value.run.id, type: 'note', tags: ['licht'],
    text: `Licht: ${form.value.light_hours} h, Stufe ${form.value.light_level}, Abstand ${form.value.lamp_distance_cm} cm` })
  say('Lichteinstellung gespeichert')
  load()
}
async function addCal() {
  await api.post(`light/${run.value.run.setup_id}/calibration`, cal.value)
  say('Messpunkt gespeichert')
  cal.value.ppfd = null
  load()
}
const band = computed(() => run.value?.light.target?.ppfd)
function cellClass(v) {
  if (!band.value || v == null) return ''
  const [lo, hi] = band.value
  if (v >= lo && v <= hi) return 'in'
  return v > hi ? 'over' : 'under'
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="run">
    <h1>Licht</h1>

    <section class="panel stack">
      <div class="row between">
        <h3>Aktuelle Einstellung</h3>
        <span class="chip" :class="rating[run.light.status]">{{ PH[run.light.phase_group] || run.light.phase_group }}</span>
      </div>
      <div class="grid3">
        <label class="field"><span>Licht (h/Tag)</span><input type="number" min="0" max="24" step="1" v-model.number="form.light_hours" /></label>
        <label class="field"><span>Stufe (1–10)</span><input type="number" min="1" max="10" step="1" v-model.number="form.light_level" /></label>
        <label class="field"><span>Abstand (cm)</span><input type="number" min="10" max="120" step="5" v-model.number="form.lamp_distance_cm" /></label>
      </div>
      <div class="grid3 result">
        <div><p class="small muted">Mitte</p><p class="num big led">{{ fmt.n(run.light.ppfd, 0) }}</p><p class="small muted">µmol/m²/s</p></div>
        <div><p class="small muted">Rand</p><p class="num big">{{ fmt.n(run.light.ppfd_edge, 0) }}</p><p class="small muted">µmol/m²/s</p></div>
        <div><p class="small muted">DLI</p><p class="num big">{{ fmt.n(run.light.dli) }}</p><p class="small muted">max. {{ run.light.target?.dli_max }}</p></div>
      </div>
      <p v-for="m in run.light.messages" :key="m" class="note warn">{{ m }}</p>
      <button class="primary" @click="save">Speichern</button>
    </section>

    <section class="stack" v-if="info">
      <h2>Empfehlungen bei {{ run.run.light_hours }} h Licht</h2>
      <div class="cols">
        <div v-for="(recs, ph) in info.recommendations" :key="ph" class="panel">
          <h3>{{ PH[ph] }}</h3>
          <p class="small muted">Ziel {{ info.targets[ph].ppfd[0] }}–{{ info.targets[ph].ppfd[1] }}, DLI bis {{ info.targets[ph].dli_max }}</p>
          <ul class="recs">
            <li v-for="r in recs" :key="r.distance_cm" class="num">
              {{ r.distance_cm }} cm, Stufe {{ r.level }} <span class="muted">({{ fmt.n(r.ppfd, 0) }}, DLI {{ fmt.n(r.dli) }}{{ r.extrapolated ? ', geschätzt' : '' }})</span>
            </li>
            <li v-if="!recs.length" class="muted">Keine passende Kombination – Lichtstunden reduzieren.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="stack" v-if="info">
      <h2>PPFD in der Zeltmitte</h2>
      <p class="small muted">Aus deiner Messung vom 27.10. hochgerechnet. Grün: Zielbereich der aktuellen Phase. Am Rand kommen etwa {{ Math.round((info.edge_factor || 0) * 100) }} % davon an.</p>
      <div class="scroll">
        <table class="heat num">
          <thead><tr><th>cm</th><th v-for="l in 10" :key="l" class="r">{{ l }}</th></tr></thead>
          <tbody>
            <tr v-for="row in info.table" :key="row.distance_cm">
              <th>{{ row.distance_cm }}</th>
              <td v-for="l in 10" :key="l" class="r" :class="[cellClass(row[l]), { est: !info.measured_levels.includes(l) || !info.measured_distances.includes(row.distance_cm) }]">{{ fmt.n(row[l], 0) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="small muted">Kursiv: geschätzt (nicht direkt gemessen). Stufe 1–2 sind hochgerechnet.</p>
    </section>

    <details class="panel">
      <summary>Messpunkt hinzufügen</summary>
      <form class="stack" style="margin-top:12px" @submit.prevent="addCal">
        <div class="grid2">
          <label class="field"><span>Abstand (cm)</span><input type="number" v-model.number="cal.distance_cm" /></label>
          <label class="field"><span>Stufe</span><input type="number" min="1" max="10" v-model.number="cal.level" /></label>
          <label class="field"><span>Punkt</span>
            <select v-model="cal.point"><option value="A">Mitte (A)</option><option v-for="p in ['B', 'C', 'D', 'E']" :key="p" :value="p">Rand {{ p }}</option></select>
          </label>
          <label class="field"><span>PPFD</span><input type="number" step="any" v-model.number="cal.ppfd" required /></label>
        </div>
        <button class="primary">Messpunkt speichern</button>
      </form>
    </details>
  </main>
</template>

<style scoped>
.big { font-size: 1.8rem; font-weight: 600; line-height: 1.1; }
.led { color: var(--led); }
.result > div { background: var(--sunken); border-radius: 10px; padding: 10px; }
.recs { padding-left: 18px; margin: 8px 0 0; }
.scroll { overflow-x: auto; }
.heat td, .heat th { padding: 6px 4px; font-size: .9rem; }
.heat td.in { background: var(--ok-bg); color: var(--leaf); font-weight: 600; }
.heat td.over { color: var(--alarm); }
.heat td.under { color: var(--muted); }
.heat td.est { font-style: italic; }
</style>
