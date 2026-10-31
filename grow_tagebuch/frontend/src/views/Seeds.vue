<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { say } from '../util.js'

const route = useRoute()
const router = useRouter()
const run = ref(null)
const strains = ref([])
const germMethods = ref([])
const f = ref(null)
const newStrain = ref(null)
const busy = ref(false)
const err = ref('')

function localNow() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}
const total = computed(() => (f.value?.rows || []).reduce((a, r) => a + (Number(r.count) || 0), 0))

async function load() {
  const r = await api.get(`runs/${route.params.id}`)
  run.value = r.run
  strains.value = await api.get('strains')
  germMethods.value = (await api.get('germination')).methods
  const all = await api.get('runs')
  const prev = all.filter((x) => x.id !== r.run.id).sort((a, b) => b.id - a.id)[0]
  const prevPlants = prev ? (await api.get(`runs/${prev.id}`)).plants : []
  const last = prevPlants.at(-1)
  f.value = {
    rows: [{ strain_id: last?.strain_id || strains.value[0]?.id, count: Math.max(prevPlants.filter((p) => p.status !== 'geerntet').length, 1) || 3 }],
    germ_method: last?.germ_method || 'h2o2', soaked_at: localNow(), pot_l: last?.pot_l || 20, pot_height_cm: last?.pot_height_cm || 30,
  }
}
async function addStrain() {
  const s = await api.post('strains', newStrain.value)
  strains.value.push(s)
  f.value.rows.at(-1).strain_id = s.id
  newStrain.value = null
}
async function save() {
  busy.value = true
  err.value = ''
  try {
    const body = { ...f.value, soaked_at: f.value.soaked_at ? `${f.value.soaked_at.slice(0, 16)}:00` : null }
    const r = await api.post(`runs/${run.value.id}/seeds`, body)
    say(r.warning || `${total.value} Samen eingetragen – „${r.run.name}“`)
    router.push('/')
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="run && f">
    <div>
      <router-link to="/" class="small muted">Später eintragen</router-link>
      <h1 style="margin-top:8px">Samen eintragen</h1>
      <p class="small muted">Neuer Durchgang mit den bisherigen Einstellungen (Zelt, Erde, Wasser, Düngeschema, Licht).
        Der Name wird automatisch aus Sorte und Saison erzeugt.</p>
    </div>

    <form class="panel stack" @submit.prevent="save">
      <div v-for="(r, i) in f.rows" :key="i" class="grid2 strainrow">
        <label class="field"><span>Sorte</span>
          <select v-model.number="r.strain_id"><option v-for="s in strains" :key="s.id" :value="s.id">{{ s.name }}<template v-if="s.breeder"> ({{ s.breeder }})</template></option></select>
        </label>
        <div class="row" style="align-items:flex-end;flex-wrap:nowrap">
          <label class="field grow"><span>Anzahl Samen</span><input type="number" min="1" max="20" v-model.number="r.count" required /></label>
          <button v-if="f.rows.length > 1" type="button" class="ghost" aria-label="Sorte entfernen" @click="f.rows.splice(i, 1)">✕</button>
        </div>
      </div>
      <div class="row">
        <button type="button" class="ghost" @click="f.rows.push({ strain_id: strains[0]?.id, count: 1 })">Weitere Sorte</button>
        <button type="button" class="ghost" v-if="!newStrain" @click="newStrain = { name: '', breeder: '', auto: true, seed_to_harvest_days: 77, max_height_cm: null }">Neue Sorte anlegen</button>
      </div>
      <div v-if="newStrain" class="sunken stack">
        <div class="grid2">
          <label class="field"><span>Sorte</span><input v-model="newStrain.name" /></label>
          <label class="field"><span>Breeder</span><input v-model="newStrain.breeder" /></label>
          <label class="field"><span>Typ</span><select v-model="newStrain.auto"><option :value="true">Autoflower</option><option :value="false">Photoperiodisch</option></select></label>
          <label class="field" v-if="newStrain.auto"><span>Samen bis Ernte (Tage)</span><input type="number" v-model.number="newStrain.seed_to_harvest_days" /></label>
          <label class="field" v-else><span>Blütedauer (Tage)</span><input type="number" v-model.number="newStrain.flowering_days" /></label>
          <label class="field"><span>Max. Höhe (cm)</span><input type="number" v-model.number="newStrain.max_height_cm" /></label>
        </div>
        <div class="row between">
          <button type="button" class="ghost" @click="newStrain = null">Zurück</button>
          <button type="button" @click="addStrain" :disabled="!newStrain.name">Sorte speichern</button>
        </div>
      </div>

      <div class="grid2">
        <label class="field"><span>Keimmethode</span>
          <select v-model="f.germ_method"><option :value="null">Keine Angabe</option><option v-for="g in germMethods" :key="g.key" :value="g.key">{{ g.name }}</option></select>
        </label>
        <label class="field"><span>Einweichen gestartet</span><input type="datetime-local" v-model="f.soaked_at" /></label>
        <label class="field"><span>Topf (l)</span><input type="number" step="any" v-model.number="f.pot_l" /></label>
        <label class="field"><span>Topfhöhe (cm)</span><input type="number" v-model.number="f.pot_height_cm" /></label>
      </div>
      <p class="small muted">Die Pflanzen heißen „Pflanze 1“, „Pflanze 2“ … – umbenennen geht jederzeit auf der Pflanzenseite.</p>
      <p v-if="err" class="note bad">{{ err }}</p>
      <button class="primary" :disabled="busy || !total">{{ total }} Samen eintragen</button>
    </form>
  </main>
</template>

<style scoped>
.strainrow { align-items: end; }
</style>
