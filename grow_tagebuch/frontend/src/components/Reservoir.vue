<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api.js'
import { fmt, say } from '../util.js'

const props = defineProps({ runId: Number })
const st = ref(null)
const schema = ref([])
const calc = ref({ stage: 'start', liters: 30, water_ec: null })
const rec = ref(null)
const entry = ref({ reservoir_action: 'wechsel', volume_l: null, ec_in: null, ph_in: null, water_temp: null, text: '' })
const busy = ref(false)
const ACTION = { wechsel: 'Komplettwechsel', nachfuellen: 'Nachfüllen', messung: 'Nur Messung' }
const stage = computed(() => schema.value.find((s) => s.key === calc.value.stage))

async function load() {
  if (!props.runId) return
  const [s, sc] = await Promise.all([api.get(`reservoir/${props.runId}`), schema.value.length ? null : api.get('reservoir/schema')])
  if (sc) schema.value = sc.stages
  st.value = s
  calc.value.stage = s.stage_suggestion
  calc.value.water_ec = s.water_ec
  if (s.status.volume_l) calc.value.liters = s.status.volume_l
  rec.value = null
}
async function compute() {
  busy.value = true
  try {
    rec.value = await api.post('reservoir/recipe', calc.value)
    entry.value.volume_l = calc.value.liters
  } catch (e) { say(e.message) } finally { busy.value = false }
}
async function save() {
  const e = entry.value
  if (e.reservoir_action !== 'messung' && !e.volume_l) { say('Menge in Litern angeben'); return }
  const products = e.reservoir_action !== 'messung' && rec.value
    ? rec.value.items.map((i) => ({ product_key: i.key, name: i.name, per_l: i.per_l, unit: 'ml',
      amount: Math.round(i.per_l * e.volume_l * 10) / 10, application: 'reservoir' }))
    : []
  await api.post('logs', { run_id: props.runId, type: 'reservoir', ...e, products,
    tags: rec.value && products.length ? [`canna:${rec.value.stage}`] : [] })
  say(`${ACTION[e.reservoir_action]} eingetragen`)
  entry.value = { reservoir_action: 'messung', volume_l: null, ec_in: null, ph_in: null, water_temp: null, text: '' }
  load()
}
async function remove(l) {
  if (!confirm('Eintrag löschen?')) return
  await api.del(`logs/${l.id}`)
  load()
}
const inRange = (v, r) => v == null || !r ? '' : v >= r[0] && v <= r[1] ? 'ok' : 'warn'
watch(() => props.runId, load)
onMounted(load)
</script>

<template>
  <div v-if="st" class="stack-lg">
    <section class="panel stack">
      <div class="row between"><h3>Zustand</h3>
        <span class="chip" :class="st.status.change_due_in == null ? '' : st.status.change_due_in <= 0 ? 'bad' : 'ok'">
          {{ st.status.days_since_change == null ? 'noch kein Ansatz' : st.status.change_due_in <= 0 ? 'Wechsel fällig' : `nächster Wechsel in ${st.status.change_due_in} d` }}</span>
      </div>
      <div class="grid4 small">
        <div class="cell"><span class="muted">Letzter Wechsel</span><span class="num">{{ st.status.last_change ? fmt.date(st.status.last_change) : '–' }}</span></div>
        <div class="cell"><span class="muted">EC</span><span class="num">{{ fmt.n(st.status.last?.ec, 2) }}</span></div>
        <div class="cell"><span class="muted">pH</span><span class="num" :class="inRange(st.status.last?.ph, st.status.ph_target)">{{ fmt.n(st.status.last?.ph) }}</span></div>
        <div class="cell"><span class="muted">Wasser{{ st.status.live_water_temp != null ? ' (live)' : '' }}</span>
          <span class="num" :class="inRange(st.status.live_water_temp ?? st.status.last?.water_temp, st.status.water_temp_target)">{{ fmt.n(st.status.live_water_temp ?? st.status.last?.water_temp) }} °C</span></div>
      </div>
      <p v-for="m in st.status.messages" :key="m" class="note warn small">{{ m }}</p>
      <p class="small muted">Ziel: pH {{ fmt.n(st.status.ph_target[0]) }}–{{ fmt.n(st.status.ph_target[1]) }}, Wasser {{ st.status.water_temp_target[0] }}–{{ st.status.water_temp_target[1] }} °C,
        Komplettwechsel etwa alle {{ st.status.change_days }} Tage (Richtwert), dazwischen mit Nährlösung nachfüllen.</p>
    </section>

    <section class="panel stack">
      <h3>Ansatz berechnen – CANNA Aqua</h3>
      <div class="grid3">
        <label class="field"><span>Phase</span>
          <select v-model="calc.stage">
            <option v-for="s in schema" :key="s.key" :value="s.key">{{ s.label }}{{ s.key === st.stage_suggestion ? ' (Vorschlag)' : '' }}</option>
          </select></label>
        <label class="field"><span>Menge (l)</span><input type="number" min="1" step="1" inputmode="decimal" v-model.number="calc.liters" /></label>
        <label class="field"><span>Wasser-EC</span><input type="number" min="0" step="0.01" inputmode="decimal" v-model.number="calc.water_ec" /></label>
      </div>
      <p v-if="stage" class="small muted">Dauer {{ stage.weeks }} Wo., Licht {{ stage.light }} laut Schema. Die App nimmt die Mitte der Herstellerspanne.</p>
      <button class="primary" :disabled="busy || !calc.liters" @click="compute">Berechnen</button>

      <template v-if="rec">
        <ol class="mix">
          <li v-for="i in rec.items" :key="i.key" class="row between">
            <span>{{ i.name }} <span class="small muted">{{ fmt.n(i.per_l, 2) }} ml/l ({{ fmt.n(i.range[0], 2) }}–{{ fmt.n(i.range[1], 2) }})</span></span>
            <strong class="num">{{ fmt.n(i.total_ml) }} ml</strong>
          </li>
        </ol>
        <p class="num"><strong>Ziel-EC {{ fmt.n(rec.ec_target[0], 2) }}–{{ fmt.n(rec.ec_target[1], 2) }}</strong>
          <span class="small muted"> (Dünger +{{ fmt.n(rec.ec_plus[0], 1) }}–{{ fmt.n(rec.ec_plus[1], 1) }}, Wasser {{ fmt.n(rec.water_ec, 2) }})</span></p>
        <ul class="small"><li v-for="n in rec.notes" :key="n">{{ n }}</li></ul>
        <p class="small muted">Quelle: <a :href="rec.source.url" target="_blank" rel="noopener">{{ rec.source.name }}</a>, abgerufen {{ fmt.date(rec.source.retrieved_on) }}</p>
      </template>
    </section>

    <section class="panel stack">
      <h3>Eintragen</h3>
      <div class="row" role="group" aria-label="Art">
        <button v-for="(l, k) in ACTION" :key="k" :class="{ primary: entry.reservoir_action === k }" @click="entry.reservoir_action = k">{{ l }}</button>
      </div>
      <div class="grid4">
        <label class="field"><span>Liter</span><input type="number" step="any" min="0" inputmode="decimal" v-model.number="entry.volume_l" :disabled="entry.reservoir_action === 'messung'" /></label>
        <label class="field"><span>EC</span><input type="number" step="0.01" min="0" inputmode="decimal" v-model.number="entry.ec_in" /></label>
        <label class="field"><span>pH</span><input type="number" step="0.1" min="0" max="14" inputmode="decimal" v-model.number="entry.ph_in" /></label>
        <label class="field"><span>Wasser °C</span><input type="number" step="0.1" inputmode="decimal" v-model.number="entry.water_temp" /></label>
      </div>
      <label class="field"><span>Notiz</span><input v-model="entry.text" placeholder="z. B. Wurzeln weiß, Schaum, Geruch" /></label>
      <p v-if="entry.reservoir_action !== 'messung'" class="small muted">{{ rec ? `Die berechneten Mengen (${rec.label}) werden für ${fmt.n(entry.volume_l)} l mitgespeichert.` : 'Ohne berechneten Ansatz wird nur Menge und Messung gespeichert.' }}</p>
      <button class="primary" @click="save">Speichern</button>
    </section>

    <section class="stack" v-if="st.logs.length">
      <h3>Verlauf</h3>
      <div v-for="l in st.logs" :key="l.id" class="panel log">
        <div class="row between"><strong>{{ ACTION[l.reservoir_action] || 'Messung' }}</strong>
          <span class="small muted">{{ fmt.dt(l.ts) }}</span></div>
        <p class="small num">
          <template v-if="l.volume_l">{{ fmt.n(l.volume_l) }} l · </template>EC {{ fmt.n(l.ec_in, 2) }} · pH {{ fmt.n(l.ph_in) }} · {{ fmt.n(l.water_temp) }} °C
        </p>
        <p v-if="l.products?.length" class="small muted">{{ l.products.map((p) => `${p.name} ${fmt.n(p.amount)} ml`).join(', ') }}</p>
        <p v-if="l.text" class="small">{{ l.text }}</p>
        <button class="ghost small" @click="remove(l)">Löschen</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.cell { background: var(--sunken); border-radius: 10px; padding: 8px 10px; display: flex; flex-direction: column; }
.cell .num { font-size: 1.2rem; font-weight: 600; }
.cell .ok { color: var(--leaf); }
.cell .warn { color: var(--amber); }
.mix { margin: 0; padding-left: 20px; }
.mix li { padding: 6px 0; border-bottom: 1px solid var(--line); gap: 8px; }
.log p { margin: 4px 0; }
.log button { align-self: flex-start; }
@media (max-width: 520px) { .grid4 { grid-template-columns: repeat(2, 1fr); } }
</style>
