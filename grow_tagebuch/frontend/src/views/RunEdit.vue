<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api.js'
import { fmt, say, today } from '../util.js'

const route = useRoute()
const run = ref(null)
const plants = ref([])
const strains = ref([])
const soils = ref([])
const waters = ref([])
const schedules = ref([])
const np = ref(null)
const newStrain = ref(null)
const germMethods = ref([])

async function load() {
  const r = await api.get(`runs/${route.params.id}`)
  run.value = r.run
  plants.value = r.plants
  ;[strains.value, soils.value, waters.value, schedules.value] = await Promise.all(
    [api.get('strains'), api.get('soils'), api.get('waters'), api.get('schedules')])
  germMethods.value = (await api.get('germination')).methods
  resetNew()
}
function resetNew() {
  np.value = { name: `Pflanze ${plants.value.length + 1}`, strain_id: strains.value[0]?.id, pot_l: 20, germ_method: plants.value.at(-1)?.germ_method || null, pot_height_cm: 30,
    soaked_on: plants.value.at(-1)?.soaked_on || today(), planted_on: plants.value.at(-1)?.planted_on || null, sprouted_on: null }
}
async function saveRun() {
  const r = run.value
  await api.patch(`runs/${r.id}`, { name: r.name, start_date: r.start_date, status: r.status, soil_id: r.soil_id,
    water_id: r.water_id, schedule_id: r.schedule_id, notes: r.notes })
  say('Durchgang gespeichert')
}
async function addPlant() {
  const p = await api.post('plants', { ...np.value, run_id: run.value.id })
  say(p.warning || `${np.value.name} angelegt`)
  load()
}
async function addStrain() {
  const s = await api.post('strains', newStrain.value)
  strains.value.push(s)
  np.value.strain_id = s.id
  newStrain.value = null
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="run">
    <router-link to="/mehr" class="small muted">Zurück</router-link>
    <h1>{{ run.name }}</h1>

    <section class="stack">
      <h2>Pflanzen</h2>
      <router-link v-for="p in plants" :key="p.id" :to="`/pflanze/${p.id}`" class="panel row between plantlink">
        <span><strong>{{ p.name }}</strong> <span class="small muted">{{ p.status }}</span></span>
        <span class="small muted">gesetzt {{ fmt.date(p.planted_on) }}, aufgelaufen {{ fmt.date(p.sprouted_on) }}</span>
      </router-link>

      <form class="panel stack" @submit.prevent="addPlant">
        <h3>Pflanze anlegen</h3>
        <div class="grid2">
          <label class="field"><span>Name</span><input v-model="np.name" required /></label>
          <label class="field"><span>Sorte</span>
            <select v-model.number="np.strain_id"><option v-for="s in strains" :key="s.id" :value="s.id">{{ s.name }} ({{ s.breeder }})</option></select>
          </label>
        </div>
        <button type="button" class="ghost" v-if="!newStrain" @click="newStrain = { name: '', breeder: '', auto: true, seed_to_harvest_days: 77, max_height_cm: null }">Neue Sorte</button>
        <div v-else class="sunken stack">
          <div class="grid2">
            <label class="field"><span>Sorte</span><input v-model="newStrain.name" /></label>
            <label class="field"><span>Breeder</span><input v-model="newStrain.breeder" /></label>
            <label class="field"><span>Typ</span><select v-model="newStrain.auto"><option :value="true">Autoflower</option><option :value="false">Photoperiodisch</option></select></label>
            <label class="field" v-if="newStrain.auto"><span>Samen bis Ernte (Tage)</span><input type="number" v-model.number="newStrain.seed_to_harvest_days" /></label>
            <label class="field" v-else><span>Blütedauer (Tage)</span><input type="number" v-model.number="newStrain.flowering_days" /></label>
            <label class="field"><span>Max. Höhe (cm)</span><input type="number" v-model.number="newStrain.max_height_cm" /></label>
          </div>
          <button type="button" @click="addStrain" :disabled="!newStrain.name">Sorte speichern</button>
        </div>
        <label class="field"><span>Keimmethode</span>
          <select v-model="np.germ_method"><option :value="null">Keine Angabe</option><option v-for="g in germMethods" :key="g.key" :value="g.key">{{ g.name }}</option></select>
        </label>
        <div class="grid3">
          <label class="field"><span>Eingeweicht</span><input type="date" v-model="np.soaked_on" /></label>
          <label class="field"><span>Gesetzt</span><input type="date" v-model="np.planted_on" /></label>
          <label class="field"><span>Aufgelaufen</span><input type="date" v-model="np.sprouted_on" /></label>
        </div>
        <div class="grid2">
          <label class="field"><span>Topf (l)</span><input type="number" step="0.5" v-model.number="np.pot_l" /></label>
          <label class="field"><span>Topfhöhe (cm)</span><input type="number" v-model.number="np.pot_height_cm" /></label>
        </div>
        <button class="primary">Pflanze anlegen</button>
      </form>
    </section>

    <form class="panel stack" @submit.prevent="saveRun">
      <h2>Durchgang</h2>
      <label class="field"><span>Name</span><input v-model="run.name" /></label>
      <div class="grid2">
        <label class="field"><span>Start</span><input type="date" v-model="run.start_date" /></label>
        <label class="field"><span>Status</span>
          <select v-model="run.status"><option v-for="s in ['geplant', 'aktiv', 'ernte', 'trocknung', 'curing', 'abgeschlossen']" :key="s">{{ s }}</option></select>
        </label>
        <label class="field"><span>Erde</span><select v-model.number="run.soil_id"><option v-for="s in soils" :key="s.id" :value="s.id">{{ s.name }}</option></select></label>
        <label class="field"><span>Wasser</span><select v-model.number="run.water_id"><option v-for="w in waters" :key="w.id" :value="w.id">{{ w.name }}</option></select></label>
      </div>
      <label class="field"><span>Düngeschema</span><select v-model.number="run.schedule_id"><option v-for="s in schedules" :key="s.id" :value="s.id">{{ s.name }}</option></select></label>
      <label class="field"><span>Notizen</span><textarea v-model="run.notes"></textarea></label>
      <button class="primary">Speichern</button>
    </form>
  </main>
</template>

<style scoped>
.plantlink { text-decoration: none; padding: 12px 16px; }
</style>
