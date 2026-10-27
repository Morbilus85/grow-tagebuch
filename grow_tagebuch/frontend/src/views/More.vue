<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt, say, today } from '../util.js'

const runs = ref([])
const soils = ref([])
const waters = ref([])
const tasks = ref([])
const setups = ref([])
const newTask = ref({ title: '', interval_days: 7, due_on: today() })
const newRun = ref(null)
const ROLES = { temp: 'Temperatur', rh: 'Luftfeuchte', vpd: 'VPD', light_level: 'Lampe Stufe', light_on: 'Lampe an/aus',
  exhaust_level: 'Abluft Stufe', heater_switch: 'Heizung', heatmat_switch: 'Heizmatte', room_temp: 'Raum Temperatur', room_rh: 'Raum Feuchte' }
const sensorEdit = ref({})
const hh = ref(null)

async function load() {
  ;[runs.value, soils.value, waters.value, tasks.value, setups.value] = await Promise.all(
    [api.get('runs'), api.get('soils'), api.get('waters'), api.get('tasks'), api.get('setups')])
  hh.value = await api.get('household')
  for (const s of setups.value) sensorEdit.value[s.id] = Object.fromEntries(Object.keys(ROLES).map((r) => [r, s.sensors.find((x) => x.role === r)?.entity_id || '']))
}
async function addTask() {
  await api.post('tasks', { ...newTask.value, run_id: runs.value.find((r) => r.status === 'aktiv')?.id })
  newTask.value = { title: '', interval_days: 7, due_on: today() }
  say('Aufgabe angelegt')
  load()
}
async function delTask(t) { if (confirm(`„${t.title}“ löschen?`)) { await api.del(`tasks/${t.id}`); load() } }
async function saveSoil(s) { await api.patch(`soils/${s.id}`, { prefertilized_weeks: s.prefertilized_weeks, worm_humus_pct: s.worm_humus_pct, schedule_type: s.schedule_type }); say('Erde gespeichert') }
async function saveWater(w) { await api.patch(`waters/${w.id}`, { ec: w.ec, ph: w.ph, ca_mg_l: w.ca_mg_l, mg_mg_l: w.mg_mg_l }); say('Wasser gespeichert') }
async function saveSensors(id) { await api.put(`setups/${id}/sensors`, sensorEdit.value[id]); say('Sensoren gespeichert') }
async function saveHousehold() {
  hh.value = await api.put('household', { adults: hh.value.adults })
  say('Haushalt gespeichert')
}
async function createRun() {
  const r = await api.post('runs', newRun.value)
  location.hash = `#/run/${r.id}`
}
function startRun() {
  const last = runs.value[0] || {}
  newRun.value = { name: '', setup_id: setups.value[0]?.id, start_date: today(), soil_id: last.soil_id, water_id: last.water_id,
    schedule_id: last.schedule_id, light_hours: 20, status: 'aktiv' }
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <h1>Mehr</h1>

    <section class="stack">
      <div class="row between"><h2>Durchgänge</h2><button class="ghost" @click="startRun">Neuer Durchgang</button></div>
      <form v-if="newRun" class="panel stack" @submit.prevent="createRun">
        <div class="grid2">
          <label class="field"><span>Name</span><input v-model="newRun.name" required /></label>
          <label class="field"><span>Setup</span><select v-model.number="newRun.setup_id"><option v-for="s in setups" :key="s.id" :value="s.id">{{ s.name }}</option></select></label>
        </div>
        <button class="primary">Durchgang anlegen</button>
      </form>
      <router-link v-for="r in runs" :key="r.id" :to="`/run/${r.id}`" class="panel row between link">
        <strong>{{ r.name }}</strong><span class="small muted">{{ r.status }}, seit {{ fmt.date(r.start_date) }}</span>
      </router-link>
    </section>

    <section class="grid2">
      <router-link to="/inventar" class="panel link"><h3>Inventar</h3><p class="small muted">Dünger, Zusätze, Dosierungen</p></router-link>
      <router-link to="/schema" class="panel link"><h3>Düngeschema</h3><p class="small muted">BioBizz All-Mix und Light-Mix</p></router-link>
      <router-link to="/training" class="panel link"><h3>Training</h3><p class="small muted">Techniken mit Anleitung, für Autos und Photos</p></router-link>
    </section>

    <section class="stack">
      <h2>Aufgaben</h2>
      <div v-for="t in tasks" :key="t.id" class="row between panel flat" style="padding:10px 12px">
        <span>{{ t.title }} <span class="small muted">{{ t.interval_days ? `alle ${t.interval_days} Tage` : 'einmalig' }}, fällig {{ fmt.date(t.due_on) }}</span></span>
        <button class="ghost" @click="delTask(t)">Löschen</button>
      </div>
      <form class="row" @submit.prevent="addTask">
        <input class="grow" style="flex:1 1 180px" v-model="newTask.title" placeholder="Neue Aufgabe" required />
        <input type="number" style="width:90px" v-model.number="newTask.interval_days" min="0" aria-label="Intervall in Tagen" />
        <input type="date" style="width:160px" v-model="newTask.due_on" aria-label="Fällig am" />
        <button>Anlegen</button>
      </form>
      <p class="small muted">Intervall 0 = einmalig.</p>
    </section>

    <section class="stack" v-if="hh">
      <h2>Haushalt & KCanG</h2>
      <div class="panel stack">
        <label class="field"><span>Erwachsene im Haushalt</span><input type="number" min="1" max="10" v-model.number="hh.adults" /></label>
        <p>{{ hh.living_plants }} von {{ hh.plant_limit }} erlaubten lebenden Pflanzen. Zu Hause aufbewahren: bis {{ hh.home_storage_limit_g }} g getrocknet.</p>
        <p class="small muted">3 Pflanzen und 50 g pro volljähriger Person am Wohnsitz; jede Pflanze sollte einer Person zuzuordnen sein. Gezählt werden gesetzte, nicht geerntete Pflanzen. Keine Rechtsberatung.</p>
        <button @click="saveHousehold">Speichern</button>
      </div>
    </section>

    <section class="stack">
      <h2>Erde</h2>
      <div v-for="s in soils" :key="s.id" class="panel stack">
        <h3>{{ s.name }}</h3>
        <p class="small muted">{{ s.components.map((c) => `${c.name} ${c.pct} %`).join(', ') }}</p>
        <div class="grid3">
          <label class="field"><span>Vorgedüngt (Wochen)</span><input type="number" v-model.number="s.prefertilized_weeks" /></label>
          <label class="field"><span>Wurmhumus (%)</span><input type="number" v-model.number="s.worm_humus_pct" /></label>
          <label class="field"><span>Schema-Typ</span><select v-model="s.schedule_type"><option value="all_mix">vorgedüngt (All-Mix)</option><option value="light_mix">schwach gedüngt (Light-Mix)</option></select></label>
        </div>
        <button @click="saveSoil(s)">Speichern</button>
      </div>
    </section>

    <section class="stack">
      <h2>Wasser</h2>
      <div v-for="w in waters" :key="w.id" class="panel stack">
        <h3>{{ w.name }}</h3>
        <div class="grid2">
          <label class="field"><span>EC</span><input type="number" step="0.01" v-model.number="w.ec" /></label>
          <label class="field"><span>pH</span><input type="number" step="0.1" v-model.number="w.ph" /></label>
          <label class="field"><span>Calcium (mg/l)</span><input type="number" step="0.1" v-model.number="w.ca_mg_l" /></label>
          <label class="field"><span>Magnesium (mg/l)</span><input type="number" step="0.1" v-model.number="w.mg_mg_l" /></label>
        </div>
        <p class="small muted">Härte {{ fmt.n(w.hardness_dh) }} °dH, Karbonathärte {{ fmt.n(w.carbonate_hardness_dh) }} °dH.
          <a v-if="w.source_url" :href="w.source_url" target="_blank" rel="noopener">Quelle</a></p>
        <button @click="saveWater(w)">Speichern</button>
      </div>
    </section>

    <section class="stack">
      <h2>Sensoren aus Home Assistant</h2>
      <div v-for="s in setups" :key="s.id" class="panel stack">
        <h3>{{ s.name }}</h3>
        <label v-for="(label, role) in ROLES" :key="role" class="field"><span>{{ label }}</span>
          <input v-model="sensorEdit[s.id][role]" placeholder="sensor.…" spellcheck="false" autocapitalize="off" /></label>
        <button @click="saveSensors(s.id)">Speichern</button>
      </div>
    </section>

    <section class="stack">
      <h2>Daten</h2>
      <a class="btn" href="api/export" download="grow-tagebuch-export.json">Alle Daten exportieren (JSON)</a>
      <p class="small muted">Fotos und Datenbank liegen im Add-on-Ordner und sind Teil der Home-Assistant-Backups.</p>
    </section>
  </main>
</template>

<style scoped>
.link { text-decoration: none; }
</style>
