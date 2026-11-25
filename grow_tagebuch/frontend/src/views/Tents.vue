<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { say } from '../util.js'

const ROLES = { temp: 'Temperatur', rh: 'Luftfeuchte', vpd: 'VPD', light_level: 'Lampe Stufe bzw. Dimmung (light.*)', light_on: 'Lampe an/aus',
  exhaust_level: 'Abluft Stufe bzw. % (fan.*)', water_temp: 'Wassertemperatur (RDWC)', heater_switch: 'Heizung', heatmat_switch: 'Heizmatte', room_temp: 'Raum Temperatur', room_rh: 'Raum Feuchte' }
const MEDIUM = { erde: 'Erde', rdwc: 'RDWC (Hydro)' }
const STATUS = { geplant: 'geplant', aktiv: 'in Betrieb', abgebaut: 'abgebaut' }
const FIELDS = ['name', 'width_cm', 'depth_cm', 'height_cm', 'lamp', 'lamp_hang_cm', 'medium', 'status', 'notes', 'leaf_offset', 'light_unit']
const UNIT = { stufe: 'Stufen 1–10 (AC Infinity)', prozent: 'Dimmung in % (z. B. 0–10 V)' }
const CAT = { zelt: 'Zelt', licht: 'Lampe', abluft: 'Abluft', filter: 'Filter', umluft: 'Umluft', controller: 'Steuerung',
  hydro: 'RDWC/Hydro', heizmatte: 'Heizmatte', heizung: 'Heizung', topf: 'Töpfe', messgeraet: 'Messgerät', sonstiges: 'Sonstiges' }
const newEq = ref({})
async function addEq(s) {
  const e = newEq.value[s.id]
  if (!e?.model) return
  await api.post(`setups/${s.id}/equipment`, e)
  newEq.value[s.id] = { category: 'sonstiges', brand: '', model: '' }
  say('Ausstattung ergänzt')
  load()
}
async function delEq(e) {
  if (!confirm(`„${e.brand} ${e.model}“ entfernen?`)) return
  await api.del(`equipment/${e.id}`)
  load()
}
const specText = (sp) => Object.entries(sp || {}).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' · ')

const setups = ref([])
const runs = ref([])
const open = ref(null)
const sensorEdit = ref({})
const newTent = ref(null)

async function load() {
  const [se, r] = await Promise.all([api.get('setups'), api.get('runs')])
  for (const s of se) newEq.value[s.id] ||= { category: 'sonstiges', brand: '', model: '' }
  for (const s of se) sensorEdit.value[s.id] = Object.fromEntries(Object.keys(ROLES).map((k) => [k, s.sensors.find((x) => x.role === k)?.entity_id || '']))
  ;[setups.value, runs.value] = [se, r]
}
const activeRun = (s) => runs.value.find((r) => r.setup_id === s.id && r.status === 'aktiv')
const size = (s) => [s.width_cm, s.depth_cm, s.height_cm].every(Boolean) ? `${s.width_cm}×${s.depth_cm}×${s.height_cm} cm` : 'Maße fehlen'

async function save(s) {
  await api.patch(`setups/${s.id}`, Object.fromEntries(FIELDS.map((k) => [k, s[k] === '' ? null : s[k]])))
  say(`${s.name} gespeichert`)
  load()
}
async function saveSensors(id) { await api.put(`setups/${id}/sensors`, sensorEdit.value[id]); say('Sensoren gespeichert') }
async function remove(s) {
  if (!confirm(`„${s.name}“ löschen? Klimaverlauf und Lichtkalibrierung dieses Zelts gehen verloren.`)) return
  try { await api.del(`setups/${s.id}`); say('Zelt gelöscht'); open.value = null; load() } catch (e) { say(e.message) }
}
async function create() {
  const s = await api.post('setups', { ...newTent.value, kind: 'zelt', indoor: true })
  newTent.value = null
  await load()
  open.value = s.id
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <div class="row between" style="margin-top:8px"><h1>Zelte</h1>
        <button class="ghost" @click="newTent = newTent ? null : { name: '', width_cm: 100, depth_cm: 100, height_cm: 200, lamp: '', medium: 'erde', status: 'geplant' }">{{ newTent ? 'Abbrechen' : 'Neues Zelt' }}</button></div>
      <p class="small muted">Jedes Zelt hat eigene Sensoren, Klimaverlauf, Klima-Alarm und Lichtkalibrierung. Durchgänge werden einem Zelt zugeordnet.</p>
    </div>

    <form v-if="newTent" class="panel stack" @submit.prevent="create">
      <label class="field"><span>Name</span><input v-model="newTent.name" placeholder="z. B. Homebox Abstellraum" required /></label>
      <div class="grid3">
        <label class="field"><span>Breite (cm)</span><input type="number" v-model.number="newTent.width_cm" /></label>
        <label class="field"><span>Tiefe (cm)</span><input type="number" v-model.number="newTent.depth_cm" /></label>
        <label class="field"><span>Höhe (cm)</span><input type="number" v-model.number="newTent.height_cm" /></label>
      </div>
      <label class="field"><span>Lampe</span><input v-model="newTent.lamp" placeholder="z. B. Spider Farmer SE5000" /></label>
      <div class="grid2">
        <label class="field"><span>Medium</span><select v-model="newTent.medium"><option v-for="(l, k) in MEDIUM" :key="k" :value="k">{{ l }}</option></select></label>
        <label class="field"><span>Status</span><select v-model="newTent.status"><option v-for="(l, k) in STATUS" :key="k" :value="k">{{ l }}</option></select></label>
      </div>
      <button class="primary">Zelt anlegen</button>
    </form>

    <section class="stack">
      <div v-for="s in setups" :key="s.id" class="panel stack">
        <button class="ghost title row between" @click="open = open === s.id ? null : s.id" :aria-expanded="open === s.id">
          <span><strong>{{ s.name }}</strong><br /><span class="small muted">{{ size(s) }} · {{ MEDIUM[s.medium] || s.medium }}{{ s.lamp ? ` · ${s.lamp}` : '' }}</span></span>
          <span class="chip" :class="{ ok: s.status === 'aktiv' }">{{ STATUS[s.status] || s.status }}</span>
        </button>
        <p class="small muted" style="margin:0">
          <template v-if="activeRun(s)">Aktiver Durchgang: <router-link :to="`/run/${activeRun(s).id}`">{{ activeRun(s).name }}</router-link></template>
          <template v-else>Kein aktiver Durchgang.</template>
          {{ s.sensors.length ? ` · ${s.sensors.length} Sensoren verknüpft` : ' · keine Sensoren' }}
        </p>

        <div v-if="open === s.id" class="stack edit">
          <label class="field"><span>Name</span><input v-model="s.name" /></label>
          <div class="grid3">
            <label class="field"><span>Breite (cm)</span><input type="number" v-model.number="s.width_cm" /></label>
            <label class="field"><span>Tiefe (cm)</span><input type="number" v-model.number="s.depth_cm" /></label>
            <label class="field"><span>Höhe (cm)</span><input type="number" v-model.number="s.height_cm" /></label>
          </div>
          <div class="grid2">
            <label class="field"><span>Lampe</span><input v-model="s.lamp" /></label>
            <label class="field"><span>Aufhängung + Lampe (cm)</span><input type="number" v-model.number="s.lamp_hang_cm" /></label>
            <label class="field"><span>Medium</span><select v-model="s.medium"><option v-for="(l, k) in MEDIUM" :key="k" :value="k">{{ l }}</option></select></label>
            <label class="field"><span>Status</span><select v-model="s.status"><option v-for="(l, k) in STATUS" :key="k" :value="k">{{ l }}</option></select></label>
          </div>
          <label class="field"><span>Lampe wird gesteuert über</span>
            <select v-model="s.light_unit"><option v-for="(l, k) in UNIT" :key="k" :value="k">{{ l }}</option></select></label>
          <label class="field"><span>Blatt kühler als Luft (°C, für Blatt-VPD)</span>
            <input type="number" inputmode="decimal" step="0.1" min="-5" max="10" v-model.number="s.leaf_offset" /></label>
          <label class="field"><span>Notiz</span><input v-model="s.notes" /></label>
          <p v-if="s.medium === 'rdwc'" class="note info small">RDWC: Unter „Gießen“ erscheint für dieses Zelt das Reservoir mit CANNA-Aqua-Rechner, Wechsel und Messwerten.</p>
          <div class="row between">
            <button class="ghost" @click="remove(s)">Löschen</button>
            <button class="primary" @click="save(s)">Speichern</button>
          </div>

          <h3>Ausstattung</h3>
          <ul class="eq">
            <li v-for="e in s.equipment" :key="e.id" class="row between">
              <span><span class="small muted">{{ CAT[e.category] || e.category }}</span><br />{{ e.brand }} {{ e.model }}
                <span v-if="specText(e.specs) || e.notes" class="small muted"><br />{{ [specText(e.specs), e.notes].filter(Boolean).join(' · ') }}</span></span>
              <button class="ghost small" @click="delEq(e)" aria-label="Entfernen">✕</button>
            </li>
          </ul>
          <div class="grid3">
            <select v-model="newEq[s.id].category" aria-label="Kategorie"><option v-for="(l, k) in CAT" :key="k" :value="k">{{ l }}</option></select>
            <input v-model="newEq[s.id].brand" placeholder="Marke" />
            <input v-model="newEq[s.id].model" placeholder="Modell" />
          </div>
          <button @click="addEq(s)" :disabled="!newEq[s.id].model">Ausstattung hinzufügen</button>

          <h3>Sensoren aus Home Assistant</h3>
          <p class="small muted">Die App liest nur, sie schaltet nichts. Leer lassen, solange das Zelt nicht steht.</p>
          <label v-for="(label, role) in ROLES" :key="role" class="field"><span>{{ label }}</span>
            <input v-model="sensorEdit[s.id][role]" placeholder="sensor.…" spellcheck="false" autocapitalize="off" /></label>
          <button @click="saveSensors(s.id)">Sensoren speichern</button>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.title { border: 0; padding: 0; min-height: 0; text-align: left; width: 100%; align-items: center; }
.edit { border-top: 1px solid var(--line); padding-top: 12px; }
h3 { margin: 8px 0 0; }
.eq { list-style: none; margin: 0; padding: 0; }
.eq li { padding: 8px 0; border-bottom: 1px solid var(--line); gap: 8px; }
</style>
