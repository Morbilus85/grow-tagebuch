<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { fmt, say } from '../util.js'

const route = useRoute()
const router = useRouter()
const runs = ref([])
const runId = ref(null)
const plants = ref([])
const products = ref([])
const sel = ref({}) // plant_id -> {on, liters}
const extras = ref([])
const cans = ref(null)
const meas = ref({})
const busy = ref(false)

const run = computed(() => runs.value.find((r) => r.run.id === runId.value))
const extraOptions = computed(() => products.value.filter((p) => p.in_stock && !['base', 'ph'].includes(p.kind)
  && !['biobizz_worm_humus', 'neem_cake'].includes(p.key)))

async function load() {
  const t = await api.get('today')
  runs.value = t.runs
  runId.value = Number(route.query.run) || t.runs[0]?.run.id
  products.value = await api.get('products')
  pick()
}
function pick() {
  const r = run.value
  if (!r) return
  plants.value = r.plants
  const only = Number(route.query.plant)
  sel.value = Object.fromEntries(r.plants.map((s) => [s.plant.id, {
    on: only ? s.plant.id === only : true,
    liters: ['seedling', 'keimung'].includes(s.phase.phase) ? 0.2 : 1,
  }]))
  cans.value = null
}
function addExtra() { extras.value.push({ product_key: extraOptions.value[0]?.key, per_l: null, application: 'giessen' }) }
async function calc() {
  busy.value = true
  try {
    const volumes = Object.fromEntries(Object.entries(sel.value).filter(([, v]) => v.on && v.liters > 0).map(([k, v]) => [k, v.liters]))
    if (!Object.keys(volumes).length) { say('Mindestens eine Pflanze mit Wassermenge wählen'); return }
    cans.value = await api.post('feeding/recipe', { run_id: runId.value, volumes, extras: extras.value.filter((e) => e.product_key) })
    meas.value = Object.fromEntries(cans.value.map((_, i) => [i, { ph_in: null, ec_in: null, ph_down_ml_total: null, text: '', teas: [] }]))
  } catch (e) { say(e.message) } finally { busy.value = false }
}
async function confirmCan(i) {
  const c = cans.value[i]
  if (c.blocks.length && !confirm('Es gibt gesperrte Zusätze – die wurden aus dem Rezept genommen. Trotzdem eintragen?')) return
  await api.post('feeding/confirm', { run_id: runId.value, recipe: c, ...meas.value[i] })
  say(`Gießen für ${c.plants.map((p) => p.name).join(', ')} eingetragen`)
  cans.value.splice(i, 1)
  if (!cans.value.length) router.push('/')
}
const stageLabel = (s) => ({ seedling: 'Sämling', veg: 'Wachstum', flush: 'Reife' }[s] || (s ? s.replace('bloom_', 'Blüte-Spalte ') : 'ohne Düngung'))
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <h1>Gießen</h1>

    <div v-if="runs.length > 1">
      <label class="field"><span>Durchgang</span>
        <select v-model.number="runId" @change="pick"><option v-for="r in runs" :key="r.run.id" :value="r.run.id">{{ r.run.name }}</option></select>
      </label>
    </div>

    <section class="panel stack" v-if="plants.length">
      <h3>Welche Pflanzen, wie viel Wasser?</h3>
      <div v-for="s in plants" :key="s.plant.id" class="row plantrow">
        <label class="row grow"><input type="checkbox" v-model="sel[s.plant.id].on" style="width:auto;min-height:auto" />
          <span>{{ s.plant.name }} <span class="small muted">{{ s.phase.label }}{{ s.phase.day ? ', Tag ' + s.phase.day : '' }}</span></span>
        </label>
        <label class="liters"><input type="number" step="0.1" min="0" inputmode="decimal" v-model.number="sel[s.plant.id].liters" :disabled="!sel[s.plant.id].on" aria-label="Liter" /><span>l</span></label>
      </div>
    </section>
    <p v-else class="muted">Keine Pflanzen im Durchgang.</p>

    <section class="stack">
      <div class="row between">
        <h3>Eigene Zusätze</h3>
        <button class="ghost" @click="addExtra">Zusatz hinzufügen</button>
      </div>
      <div v-for="(e, i) in extras" :key="i" class="extra">
        <select v-model="e.product_key"><option v-for="p in extraOptions" :key="p.key" :value="p.key">{{ p.name }}</option></select>
        <input type="number" step="0.1" min="0" inputmode="decimal" placeholder="pro Liter" v-model.number="e.per_l" />
        <select v-model="e.application"><option value="giessen">Gießen</option><option value="spray">Spray</option></select>
        <button class="ghost" @click="extras.splice(i, 1)" aria-label="Entfernen">✕</button>
      </div>
      <p class="small muted" v-if="!extras.length">Optional, z. B. Melasse oder Schachtelhalm. Die App prüft die Regeln.</p>
    </section>

    <button class="primary" :disabled="busy" @click="calc">Rezept berechnen</button>

    <article v-for="(c, i) in cans" :key="i" class="panel stack can">
      <div class="row between">
        <h2>Kanne {{ cans.length > 1 ? i + 1 : '' }}: {{ fmt.n(c.total_l) }} l</h2>
        <span class="chip">{{ stageLabel(c.stage) }}</span>
      </div>
      <p class="small muted">Für {{ c.plants.map((p) => `${p.name} (${fmt.n(p.volume_l)} l)`).join(', ') }}</p>

      <p v-for="b in c.blocks" :key="b" class="note bad">{{ b }}</p>
      <p v-for="w in c.warnings" :key="w" class="note warn">{{ w }}</p>

      <table v-if="c.items.length">
        <thead><tr><th>Produkt</th><th class="r">pro l</th><th class="r">in die Kanne</th></tr></thead>
        <tbody>
          <tr v-for="it in c.items" :key="it.key">
            <td>{{ it.name }}<br /><span class="small muted">{{ it.note }}</span></td>
            <td class="r num">{{ it.per_l !== null ? fmt.n(it.per_l) + ' ' + it.unit : '–' }}</td>
            <td class="r num total">{{ it.total !== null ? fmt.n(it.total) + ' ' + it.unit : 'laut Etikett' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="sunken">Nur Wasser.</p>

      <details v-if="c.skipped.length">
        <summary class="small muted">{{ c.skipped.length }} Produkte aus dem Schema weggelassen</summary>
        <ul class="small"><li v-for="s in c.skipped" :key="s.name">{{ s.name }}: {{ s.reason }}</li></ul>
      </details>
      <ul class="small muted" v-if="c.info.length"><li v-for="x in c.info" :key="x">{{ x }}</li></ul>

      <div v-if="c.suggestions?.length" class="stack">
        <h3>Tees & Top-Dress</h3>
        <label v-for="t in c.suggestions" :key="t.key" class="row tea">
          <input type="checkbox" :value="t.key" v-model="meas[i].teas" />
          <span class="grow">{{ t.name }} <span class="chip" :class="t.due ? 'ok' : ''">{{ t.due ? 'fällig' : 'zuletzt ' + fmt.date(t.last) }}</span><br />
            <span class="small muted">{{ t.summary }} <router-link :to="{ path: '/living-soil', query: { tab: 'tees' } }">Anleitung</router-link></span></span>
        </label>
        <p class="small muted">Anhaken, was du dieser Kanne beigibst – die App merkt sich den Termin.</p>
      </div>

      <div class="sunken stack">
        <p><strong>pH {{ fmt.n(c.ph.target[0]) }}–{{ fmt.n(c.ph.target[1]) }}</strong>
          <span class="small muted"> Leitungswasser pH {{ fmt.n(c.ph.tap_ph) }}</span></p>
        <p class="small" v-if="c.ph.bio_down_ml_per_l">Erfahrungswert Bio-Down: ca. {{ fmt.n(c.ph.bio_down_ml_per_l, 2) }} ml/l, also {{ fmt.n(c.ph.bio_down_ml_per_l * c.total_l, 2) }} ml für diese Kanne.</p>
        <p class="small muted">{{ c.ph.note }} {{ c.ec.note }}</p>
      </div>

      <div class="grid3">
        <label class="field"><span>pH gemessen</span><input type="number" step="0.1" inputmode="decimal" v-model.number="meas[i].ph_in" /></label>
        <label class="field"><span>EC gemessen</span><input type="number" step="0.01" inputmode="decimal" v-model.number="meas[i].ec_in" /></label>
        <label class="field"><span>Bio-Down (ml)</span><input type="number" step="0.05" inputmode="decimal" v-model.number="meas[i].ph_down_ml_total" /></label>
      </div>
      <label class="field"><span>Notiz</span><input v-model="meas[i].text" /></label>
      <button class="primary" @click="confirmCan(i)">Gießen eintragen</button>
    </article>
  </main>
</template>

<style scoped>
.plantrow { flex-wrap: nowrap; }
.tea { align-items: flex-start; flex-wrap: nowrap; }
.tea input { margin-top: 4px; }
.liters { display: flex; align-items: center; gap: 6px; width: 110px; }
.extra { display: grid; grid-template-columns: 1fr 96px 96px 44px; gap: 6px; }
.total { font-weight: 600; font-size: 1.15rem; }
td.r, th.r { white-space: nowrap; }
@media (max-width: 420px) { .extra { grid-template-columns: 1fr 1fr; } }
</style>
