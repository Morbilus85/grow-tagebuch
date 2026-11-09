<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt, today } from '../util.js'

const runs = ref([])
const setups = ref([])
const newRun = ref(null)
async function load() { [runs.value, setups.value] = await Promise.all([api.get('runs'), api.get('setups')]) }
async function createRun() {
  const r = await api.post('runs', newRun.value)
  location.hash = `#/run/${r.id}/samen`
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
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <div class="row between" style="margin-top:8px"><h1>Durchgänge</h1><button class="ghost" @click="newRun ? (newRun = null) : startRun()">{{ newRun ? 'Abbrechen' : 'Neuer Durchgang' }}</button></div>
    </div>
    <form v-if="newRun" class="panel stack" @submit.prevent="createRun">
      <div class="grid2">
        <label class="field"><span>Name</span><input v-model="newRun.name" placeholder="automatisch (Sorte – Saison)" /></label>
        <label class="field"><span>Setup</span><select v-model.number="newRun.setup_id"><option v-for="s in setups" :key="s.id" :value="s.id">{{ s.name }}</option></select></label>
      </div>
      <button class="primary">Weiter zu den Samen</button>
    </form>
    <section class="stack">
      <router-link v-for="r in runs" :key="r.id" :to="`/run/${r.id}`" class="panel row between link">
        <strong>{{ r.name }}</strong><span class="small muted">{{ r.status }}, seit {{ fmt.date(r.start_date) }}</span>
      </router-link>
      <p v-if="!runs.length" class="muted">Noch kein Durchgang.</p>
    </section>
  </main>
</template>

<style scoped>.link { text-decoration: none; }</style>
