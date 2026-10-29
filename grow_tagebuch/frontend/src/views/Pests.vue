<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { fmt, PEST, say, shrinkImage } from '../util.js'

const route = useRoute()
const router = useRouter()
const catalog = ref(null)
const cases = ref([])
const runs = ref([])
const plants = ref([])
const form = ref(null)
const file = ref(null)
const busy = ref(false)

const runId = computed(() => runs.value.find((r) => r.status === 'aktiv')?.id || runs.value[0]?.id)
const pestByCat = computed(() => {
  const g = {}
  for (const p of catalog.value?.pests || []) (g[p.category] ||= []).push(p)
  return g
})
const open = computed(() => cases.value.filter((c) => c.status !== 'erledigt'))
const closed = computed(() => cases.value.filter((c) => c.status === 'erledigt'))

async function load() {
  ;[catalog.value, runs.value] = await Promise.all([api.get('pests/catalog'), api.get('runs')])
  if (runId.value) {
    cases.value = await api.get(`pests/cases?run_id=${runId.value}`)
    plants.value = (await api.get(`runs/${runId.value}`)).plants.filter((p) => p.status === 'aktiv')
  }
  if (route.query.neu !== undefined && !form.value) start()
}
function start() {
  const pre = Number(route.query.plant) || null
  form.value = { pest_key: 'trauermuecken', name: '', scope: 'zelt', plant_ids: pre ? [pre] : [], severity: 1, text: '' }
}
function pickPest() {
  const p = catalog.value.pests.find((x) => x.key === form.value.pest_key)
  form.value.scope = p.default_scope === 'zelt' ? 'zelt' : 'pflanzen'
}
async function create() {
  const f = form.value
  if (f.scope === 'pflanzen' && !f.plant_ids.length) { say('Bitte mindestens eine Pflanze wählen'); return }
  if (f.pest_key === 'sonstiges' && !f.name) { say('Bitte einen Namen eingeben'); return }
  busy.value = true
  try {
    const c = await api.post('pests/cases', { ...f, run_id: runId.value })
    if (file.value && c.logs[0]) {
      try { await api.upload(`logs/${c.logs[0].id}/photos`, await shrinkImage(file.value)) } catch (e) { say(`Befall angelegt, Foto fehlgeschlagen: ${e.message}`) }
    }
    router.push(`/schaedlinge/${c.id}`)
  } finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="catalog">
    <router-link to="/mehr" class="small muted">Zurück</router-link>
    <div class="row between">
      <h1>Schädlinge & Krankheiten</h1>
      <button v-if="!form" class="primary" @click="start">Befall melden</button>
    </div>

    <form v-if="form" class="panel stack" @submit.prevent="create">
      <h3>Befall melden</h3>
      <label class="field"><span>Was ist es?</span>
        <select v-model="form.pest_key" @change="pickPest">
          <optgroup v-for="(list, cat) in pestByCat" :key="cat" :label="catalog.categories[cat]">
            <option v-for="p in list" :key="p.key" :value="p.key">{{ p.name }}</option>
          </optgroup>
        </select>
      </label>
      <label v-if="form.pest_key === 'sonstiges'" class="field"><span>Bezeichnung</span><input v-model="form.name" placeholder="z. B. Blattflecken unklar" /></label>
      <div class="field">
        <span class="small muted">Betrifft</span>
        <div class="row">
          <button type="button" :class="{ primary: form.scope === 'zelt' }" @click="form.scope = 'zelt'">Ganzes Zelt</button>
          <button type="button" :class="{ primary: form.scope === 'pflanzen' }" @click="form.scope = 'pflanzen'">Einzelne Pflanzen</button>
        </div>
      </div>
      <div v-if="form.scope === 'pflanzen'" class="row">
        <label v-for="p in plants" :key="p.id" class="row chipbox"><input type="checkbox" :value="p.id" v-model="form.plant_ids" /> {{ p.name }}</label>
      </div>
      <label class="field"><span>Stärke</span>
        <select v-model.number="form.severity"><option v-for="(l, k) in PEST.severity" :key="k" :value="Number(k)">{{ l }}</option></select>
      </label>
      <label class="field"><span>Befund</span><textarea v-model="form.text" placeholder="Was hast du gesehen? z. B. 8 Mücken auf der Gelbtafel, Larven in der Erde"></textarea></label>
      <label class="field"><span>Foto (optional)</span><input type="file" accept="image/*" @change="file = $event.target.files[0]" /></label>
      <div class="row between"><button type="button" class="ghost" @click="form = null">Abbrechen</button><button class="primary" :disabled="busy">Befall anlegen</button></div>
    </form>

    <section class="stack">
      <h2>Offen</h2>
      <p v-if="!open.length" class="muted">Keine offenen Befälle.</p>
      <router-link v-for="c in open" :key="c.id" :to="`/schaedlinge/${c.id}`" class="panel case">
        <div class="row between"><h3>{{ c.name }}</h3><span class="chip" :class="PEST.statusClass[c.status]">{{ PEST.status[c.status] }}</span></div>
        <p class="small muted">{{ PEST.scope(c, plants) }}, {{ PEST.severity[c.severity] }}, seit {{ fmt.date(c.started_on) }}<template v-if="c.open_tasks">, {{ c.open_tasks }} Folgetermin(e)</template></p>
      </router-link>
    </section>

    <section v-if="closed.length" class="stack">
      <h2>Erledigt</h2>
      <router-link v-for="c in closed" :key="c.id" :to="`/schaedlinge/${c.id}`" class="panel case flat">
        <div class="row between"><strong>{{ c.name }}</strong><span class="small muted">{{ fmt.date(c.started_on) }} – {{ fmt.date(c.closed_on) }}</span></div>
      </router-link>
    </section>
  </main>
</template>

<style scoped>
.case { display: block; text-decoration: none; }
.case > * + * { margin-top: 4px; }
.chipbox { background: var(--sunken); border-radius: 999px; padding: 6px 12px; }
</style>
