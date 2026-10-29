<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { fmt, say, today } from '../util.js'

const route = useRoute()
const router = useRouter()
const data = ref(null)
const plant = ref(null)
const runPlants = ref([])
const calc = ref({ stock: 3, water: 100, target: 0.3 })

const key = computed(() => route.params.key)
const m = computed(() => data.value?.methods.find((x) => x.key === key.value))
const plantId = computed(() => Number(route.query.plant) || null)
const ml = computed(() => {
  const { stock, water, target } = calc.value
  if (!stock || !water || !target || target >= stock) return null
  return (water * target) / (stock - target)
})

async function load() {
  if (!data.value) data.value = await api.get('germination')
  if (m.value?.calculator) calc.value = { stock: m.value.calculator.default_stock_pct, water: m.value.calculator.default_water_ml, target: m.value.calculator.target_pct }
  if (plantId.value) {
    plant.value = (await api.get(`plants/${plantId.value}`)).plant
    runPlants.value = (await api.get(`runs/${plant.value.run_id}`)).plants.filter((p) => !p.sprouted_on && !p.planted_on)
  }
}
function localNow() {
  const d = new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
  return d.toISOString().slice(0, 19)
}
async function choose(start) {
  const targets = runPlants.value.length ? runPlants.value : [plant.value]
  const body = { germ_method: key.value }
  if (start) Object.assign(body, { soaked_on: today(), soaked_at: localNow() })
  for (const p of targets) await api.patch(`plants/${p.id}`, body)
  say(start ? `Einweichen gestartet (${targets.length} ${targets.length === 1 ? 'Pflanze' : 'Pflanzen'})` : 'Methode übernommen')
  router.push(`/pflanze/${plantId.value}`)
}
watch(key, load)
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="data">
    <router-link :to="plantId ? `/pflanze/${plantId}` : key ? { path: '/keimung', query: route.query } : '/mehr'" class="small muted">
      {{ plantId && !key ? 'Zurück zur Pflanze' : 'Zurück' }}
    </router-link>

    <template v-if="!m">
      <h1>Keimung</h1>
      <p class="muted">Wähle eine Methode – du bekommst Anleitung, Mischverhältnis und den passenden Zeitplan für deine Pflanzen.</p>
      <router-link v-for="x in data.methods" :key="x.key" :to="{ path: `/keimung/${x.key}`, query: route.query }" class="panel method">
        <div class="row between"><h3>{{ x.name }}</h3><span class="small muted">{{ x.duration }}</span></div>
        <p class="small muted" v-if="x.aka">{{ x.aka }}</p>
        <p class="small">{{ x.summary }}</p>
      </router-link>
      <section class="stack">
        <h2>Grundregeln</h2>
        <ul><li v-for="g in data.general" :key="g">{{ g }}</li></ul>
      </section>
    </template>

    <template v-else>
      <div>
        <h1>{{ m.name }}</h1>
        <p class="muted" v-if="m.aka">{{ m.aka }}</p>
      </div>
      <p class="lead">{{ m.summary }}</p>
      <div class="grid2 facts">
        <div><p class="small muted">Dauer</p><p>{{ m.duration }}</p></div>
        <div><p class="small muted">Temperatur</p><p>{{ m.temperature }}</p></div>
      </div>

      <section v-if="m.calculator" class="panel stack">
        <h3>Mischung berechnen</h3>
        <div class="grid3">
          <label class="field"><span>H₂O₂ laut Flasche (%)</span><input type="number" step="any" min="1" v-model.number="calc.stock" /></label>
          <label class="field"><span>Wasser (ml)</span><input type="number" step="10" min="10" v-model.number="calc.water" /></label>
          <label class="field"><span>Ziel (%)</span><input type="number" step="any" :min="m.calculator.range_pct[0]" :max="m.calculator.range_pct[1]" v-model.number="calc.target" /></label>
        </div>
        <p class="result" v-if="ml !== null">{{ fmt.n(ml, 1) }} ml H₂O₂ ({{ fmt.n(calc.stock) }} %) in {{ fmt.n(calc.water, 0) }} ml Wasser</p>
        <p class="small muted">Üblich sind {{ fmt.n(m.calculator.range_pct[0]) }}–{{ fmt.n(m.calculator.range_pct[1]) }} % Endkonzentration. Für ein paar Samen reichen 50–100 ml Lösung. Konzentration auf der Flasche prüfen – 12 % ist viermal so stark wie 3 %.</p>
      </section>

      <section class="stack">
        <h2>So geht's</h2>
        <ol class="steps"><li v-for="s in m.steps" :key="s">{{ s }}</li></ol>
      </section>

      <section v-if="m.timeline?.length" class="stack">
        <h3>Zeitplan</h3>
        <ul class="tl"><li v-for="t in m.timeline" :key="t.hours"><span class="num">{{ t.hours }} h</span> {{ t.text }}</li></ul>
      </section>

      <div class="grid2">
        <section class="stack"><h3>Vorteile</h3><ul><li v-for="p in m.pros" :key="p">{{ p }}</li></ul></section>
        <section class="stack"><h3>Nachteile</h3><ul><li v-for="p in m.cons" :key="p">{{ p }}</li></ul></section>
      </div>
      <section class="stack"><h3>Typische Fehler</h3><ul><li v-for="p in m.mistakes" :key="p">{{ p }}</li></ul></section>
      <section class="stack"><h3>Material</h3><p>{{ m.materials.join(', ') }}</p></section>

      <div v-if="plant" class="panel stack">
        <h3>Für {{ runPlants.length > 1 ? `${runPlants.length} Pflanzen im Durchgang` : plant.name }}</h3>
        <p class="small muted" v-if="runPlants.length > 1">Gilt für alle Pflanzen, die noch nicht eingesetzt sind: {{ runPlants.map((p) => p.name).join(', ') }}.</p>
        <div class="row">
          <button class="primary" v-if="m.timeline?.length" @click="choose(true)">Einweichen jetzt starten</button>
          <button @click="choose(false)">Methode übernehmen</button>
        </div>
      </div>
    </template>
  </main>
</template>

<style scoped>
.method { display: block; text-decoration: none; }
.method > * + * { margin-top: 6px; }
.lead { font-size: 1.1rem; }
.facts > div { background: var(--sunken); border-radius: 10px; padding: 10px; }
.result { font-family: var(--cond); font-size: 1.5rem; font-weight: 600; color: var(--leaf); }
.steps { padding-left: 22px; }
.steps li { margin: 8px 0; padding-left: 4px; }
ul { padding-left: 20px; }
ul li { margin: 6px 0; }
.tl { list-style: none; padding: 0; }
.tl .num { display: inline-block; min-width: 48px; font-weight: 600; color: var(--leaf); }
</style>
