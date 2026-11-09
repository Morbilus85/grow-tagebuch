<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api.js'
import { fmt, today } from '../util.js'

const runs = ref([])
const setups = ref([])
const newRun = ref(null)
const route = useRoute()
async function load() {
  [runs.value, setups.value] = await Promise.all([api.get('runs'), api.get('setups')])
  if (route.query.neu && !newRun.value) startRun(Number(route.query.zelt) || null)
}
async function createRun() {
  const r = await api.post('runs', newRun.value)
  location.hash = `#/run/${r.id}/samen`
}
function startRun(setupId = null) {
  const last = runs.value[0] || {}
  // Vorauswahl: gewünschtes Zelt, sonst das erste Zelt ohne aktiven Durchgang
  const busy = new Set(runs.value.filter((r) => r.status === 'aktiv').map((r) => r.setup_id))
  const free = setups.value.filter((s) => s.status !== 'abgebaut').find((s) => !busy.has(s.id))
  newRun.value = { name: '', setup_id: setupId || free?.id || setups.value[0]?.id, start_date: today(), soil_id: last.soil_id, water_id: last.water_id,
    schedule_id: last.schedule_id, light_hours: 20, status: 'aktiv' }
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <div class="row between" style="margin-top:8px"><h1>Durchgänge</h1><button class="ghost" @click="newRun ? (newRun = null) : startRun()">{{ newRun ? 'Abbrechen' : 'Neuer Durchgang' }}</button></div>
    </div>
    <form v-if="newRun" class="panel stack" @submit.prevent="createRun">
      <div class="grid2">
        <label class="field"><span>Name</span><input v-model="newRun.name" placeholder="automatisch (Sorte – Saison)" /></label>
        <label class="field"><span>Zelt</span><select v-model.number="newRun.setup_id"><option v-for="s in setups.filter((x) => x.status !== 'abgebaut')" :key="s.id" :value="s.id">{{ s.name }}{{ s.status === 'geplant' ? ' (geplant)' : '' }}</option></select></label>
      </div>
      <button class="primary">Weiter zu den Samen</button>
    </form>
    <section class="stack">
      <router-link v-for="r in runs" :key="r.id" :to="`/run/${r.id}`" class="panel row between link">
        <span><strong>{{ r.name }}</strong><br /><span class="small muted">{{ setups.find((s) => s.id === r.setup_id)?.name }}</span></span><span class="small muted">{{ r.status }}, seit {{ fmt.date(r.start_date) }}</span>
      </router-link>
      <p v-if="!runs.length" class="muted">Noch kein Durchgang.</p>
    </section>
  </main>
</template>

<style scoped>.link { text-decoration: none; }</style>
