<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt, say } from '../util.js'

const soils = ref([])
const waters = ref([])
const aiOk = ref(true)
const busy = ref({})
const err = ref({})
const newSoil = ref(null)

const SCHEMA = { all_mix: 'vorgedüngt (All-Mix)', light_mix: 'schwach gedüngt (Light-Mix)', living_soil: 'Living Soil (nur Wasser, Tees)' }
const WATER_FIELDS = [
  ['ec', 'EC (mS/cm)'], ['ph', 'pH'], ['ca_mg_l', 'Calcium (mg/l)'], ['mg_mg_l', 'Magnesium (mg/l)'],
  ['hardness_dh', 'Gesamthärte (°dH)'], ['carbonate_hardness_dh', 'Karbonathärte (°dH)'], ['acid_capacity_mmol', 'Säurekap. (mmol/l)'],
  ['na_mg_l', 'Natrium (mg/l)'], ['k_mg_l', 'Kalium (mg/l)'], ['cl_mg_l', 'Chlorid (mg/l)'], ['so4_mg_l', 'Sulfat (mg/l)'], ['no3_mg_l', 'Nitrat (mg/l)'],
]
const NUTRIENTS = [['n_mg_l', 'N', 'mg/l'], ['p2o5_mg_l', 'P₂O₅', 'mg/l'], ['k2o_mg_l', 'K₂O', 'mg/l'], ['mg_mg_l', 'Mg', 'mg/l'], ['salt_g_l', 'Salz', 'g/l']]

async function load() {
  const [s, w, ai] = await Promise.all([api.get('soils'), api.get('waters'), api.get('ai/status')])
  soils.value = s.map((x) => ({ ...x, info: x.info || {} }))
  waters.value = w.map((x) => ({ ...x, info: x.info || {} }))
  aiOk.value = ai.available
}

async function research(kind, obj, body) {
  const k = `${kind}${obj.id}`
  busy.value[k] = true
  err.value[k] = ''
  try {
    const r = await api.post(`${kind}s/${obj.id}/refresh`, body)
    Object.assign(obj, r, { info: r.info || {} })
    say(kind === 'water' ? 'Wasserwerte aktualisiert' : 'Steckbrief aktualisiert')
  } catch (e) {
    // HA-Ingress trennt nach ca. 30 s – die Recherche läuft weiter, also nachladen
    err.value[k] = e.message.startsWith('5') && !e.message.includes(' ')
      ? 'Verbindung getrennt, die Recherche läuft weiter. In etwa einer Minute neu laden.' : e.message
  } finally { busy.value[k] = false }
}

async function saveWater(w) {
  await api.patch(`waters/${w.id}`, { ...Object.fromEntries(WATER_FIELDS.map(([k]) => [k, w[k] === '' ? null : w[k]])), city: w.city })
  say('Wasser gespeichert')
}
async function saveSoil(s) {
  await api.patch(`soils/${s.id}`, { name: s.name, product: s.product, prefertilized_weeks: s.prefertilized_weeks,
    worm_humus_pct: s.worm_humus_pct, schedule_type: s.schedule_type })
  say('Erde gespeichert')
}
async function adopt(s) {
  if (s.info.nutrient_weeks) s.prefertilized_weeks = s.info.nutrient_weeks
  if (s.info.schedule_type) s.schedule_type = s.info.schedule_type
  await saveSoil(s)
}
// Nur die Herstellerangaben nennen, die von der Einstellung abweichen
function diffText(s) {
  const out = []
  if (s.info.nutrient_weeks && s.info.nutrient_weeks !== s.prefertilized_weeks)
    out.push(`${s.info.nutrient_weeks} Wochen vorgedüngt (eingestellt: ${s.prefertilized_weeks})`)
  if (s.info.schedule_type && s.info.schedule_type !== s.schedule_type)
    out.push(`${SCHEMA[s.info.schedule_type]} (eingestellt: ${SCHEMA[s.schedule_type]})`)
  return out.join(', ')
}
async function createSoil() {
  const s = await api.post('soils', { name: newSoil.value.name || newSoil.value.product, product: newSoil.value.product,
    schedule_type: 'all_mix', prefertilized_weeks: 4 })
  newSoil.value = null
  await load()
  if (aiOk.value && s.product) research('soil', soils.value.find((x) => x.id === s.id), { product: s.product })
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1 style="margin-top:8px">Erde & Wasser</h1>
      <p class="small muted">Grundlage für Düngeplan, pH-Korrektur und CalMag. Werte lassen sich aus dem Internet holen und danach von Hand anpassen.</p>
      <p v-if="!aiOk" class="note">Für den Internet-Abruf wird ein Claude-API-Schlüssel gebraucht: Add-on → Konfiguration → anthropic_api_key.</p>
    </div>

    <!-- Wasser -->
    <section class="stack">
      <h2>Wasser</h2>
      <div v-for="w in waters" :key="w.id" class="panel stack">
        <div class="row between"><h3>{{ w.name }}</h3><span v-if="w.info.hardness_range" class="small muted">{{ w.info.hardness_range }}</span></div>

        <form class="row" @submit.prevent="research('water', w, { city: w.city })">
          <input class="grow" style="flex:1 1 200px" v-model="w.city" placeholder="Ort, ggf. Stadtteil – z. B. Essen-Rüttenscheid" />
          <button class="primary" :disabled="!aiOk || busy['water' + w.id] || !w.city">{{ busy['water' + w.id] ? 'Recherchiere … (bis zu 1 Minute)' : 'Wasserwerte holen' }}</button>
        </form>
        <p v-if="err['water' + w.id]" class="note bad">{{ err['water' + w.id] }}</p>

        <p v-if="w.info.supplier" class="small">
          <strong>{{ w.info.supplier }}</strong><template v-if="w.info.supply_area"> · {{ w.info.supply_area }}</template><template v-if="w.info.analysis_date"> · Stand {{ w.info.analysis_date }}</template>
        </p>
        <ul v-if="w.info.notes?.length" class="small notes"><li v-for="n in w.info.notes" :key="n">{{ n }}</li></ul>

        <div class="grid3">
          <label v-for="[k, label] in WATER_FIELDS" :key="k" class="field"><span>{{ label }}</span><input type="number" step="any" v-model.number="w[k]" /></label>
        </div>
        <p class="small muted">
          <template v-if="w.info.updated_at">Stand {{ fmt.dateLong(w.info.updated_at) }}, aus dem Internet recherchiert. </template>
          <template v-if="w.info.sources?.length">Quellen: <template v-for="(q, n) in w.info.sources" :key="q.url"><a :href="q.url" target="_blank" rel="noopener">{{ q.title }}</a><template v-if="n < w.info.sources.length - 1">, </template></template></template>
          <a v-else-if="w.source_url" :href="w.source_url" target="_blank" rel="noopener">Quelle</a>
        </p>
        <button @click="saveWater(w)">Speichern</button>
      </div>
    </section>

    <!-- Erde -->
    <section class="stack">
      <div class="row between"><h2>Erde</h2><button class="ghost" @click="newSoil = newSoil ? null : { name: '', product: '' }">{{ newSoil ? 'Abbrechen' : 'Neue Erde' }}</button></div>
      <form v-if="newSoil" class="panel stack" @submit.prevent="createSoil">
        <label class="field"><span>Produkt (für die Recherche)</span><input v-model="newSoil.product" placeholder="z. B. BioBizz Light-Mix" required /></label>
        <label class="field"><span>Eigener Name (optional)</span><input v-model="newSoil.name" placeholder="z. B. Light-Mix + 15 % Wurmhumus" /></label>
        <button class="primary">Anlegen{{ aiOk ? ' und Steckbrief holen' : '' }}</button>
      </form>

      <div v-for="s in soils" :key="s.id" class="panel stack">
        <h3>{{ s.name }}</h3>
        <p v-if="s.components?.length" class="small muted">Deine Mischung: {{ s.components.map((c) => `${c.name} ${c.pct} %`).join(', ') }}</p>

        <form class="row" @submit.prevent="research('soil', s, { product: s.product })">
          <input class="grow" style="flex:1 1 200px" v-model="s.product" placeholder="Produkt, z. B. Floragard Grow Mix Organic" />
          <button class="primary" :disabled="!aiOk || busy['soil' + s.id] || !s.product">{{ busy['soil' + s.id] ? 'Recherchiere … (bis zu 1 Minute)' : 'Steckbrief holen' }}</button>
        </form>
        <p v-if="err['soil' + s.id]" class="note bad">{{ err['soil' + s.id] }}</p>

        <div v-if="s.info.updated_at" class="stack brief">
          <p class="small"><strong>{{ s.info.product || s.product }}</strong><template v-if="s.info.manufacturer"> · {{ s.info.manufacturer }}</template></p>
          <div class="facts">
            <div v-if="s.info.fertilization"><span class="small muted">Düngung</span>{{ s.info.fertilization }}</div>
            <div v-if="s.info.nutrient_weeks"><span class="small muted">Reicht laut Hersteller</span>{{ s.info.nutrient_weeks }} Wochen</div>
            <div v-if="s.info.ph"><span class="small muted">pH</span>{{ s.info.ph }}</div>
            <div v-if="s.info.organic"><span class="small muted">Bio</span>{{ s.info.organic }}</div>
            <div v-for="[k, l, u] in NUTRIENTS.filter(([k]) => s.info[k])" :key="k"><span class="small muted">{{ l }}</span>{{ fmt.n(s.info[k], 2) }} {{ u }}</div>
          </div>
          <p v-if="s.info.components?.length" class="small"><span class="muted">Zusammensetzung:</span> {{ s.info.components.map((c) => c.share ? `${c.name} (${c.share})` : c.name).join(', ') }}</p>
          <p v-if="s.info.fertilizers?.length" class="small"><span class="muted">Enthaltene Dünger:</span> {{ s.info.fertilizers.join(', ') }}</p>
          <p v-if="s.info.structure" class="small"><span class="muted">Struktur:</span> {{ s.info.structure }}</p>
          <div v-if="s.info.feeding_notes?.length">
            <h4>Abstimmung mit deinem Dünger</h4>
            <ul class="small notes"><li v-for="n in s.info.feeding_notes" :key="n">{{ n }}</li></ul>
          </div>
          <ul v-if="s.info.specials?.length" class="small notes muted"><li v-for="n in s.info.specials" :key="n">{{ n }}</li></ul>
          <p class="small muted">Stand {{ fmt.dateLong(s.info.updated_at) }}, aus dem Internet recherchiert.
            <template v-if="s.info.sources?.length">Quellen: <template v-for="(q, n) in s.info.sources" :key="q.url"><a :href="q.url" target="_blank" rel="noopener">{{ q.title }}</a><template v-if="n < s.info.sources.length - 1">, </template></template></template></p>
          <div v-if="diffText(s)" class="note info row between">
            <span class="small">Laut Hersteller: {{ diffText(s) }}.</span>
            <button class="ghost small" @click="adopt(s)">Übernehmen</button>
          </div>
        </div>

        <h4>Für den Düngeplan</h4>
        <div class="grid2">
          <label class="field"><span>Vorgedüngt (Wochen)</span><input type="number" v-model.number="s.prefertilized_weeks" /></label>
          <label class="field"><span>Wurmhumus (%)</span><input type="number" v-model.number="s.worm_humus_pct" /></label>
        </div>
        <label class="field"><span>Schema-Typ</span><select v-model="s.schedule_type"><option v-for="(l, k) in SCHEMA" :key="k" :value="k">{{ l }}</option></select></label>
        <button @click="saveSoil(s)">Speichern</button>
      </div>
    </section>
  </main>
</template>

<style scoped>
h4 { margin: 4px 0 0; font-size: .95rem; }
.notes { margin: 0; padding-left: 18px; }
.notes li + li { margin-top: 4px; }
.brief { border-top: 1px solid var(--line); padding-top: 12px; }
.facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; }
.facts > div { background: var(--sunken); border-radius: 10px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
@media (max-width: 520px) { .grid3 { grid-template-columns: 1fr 1fr; } }
</style>
