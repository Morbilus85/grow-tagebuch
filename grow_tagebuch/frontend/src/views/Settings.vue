<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt, say } from '../util.js'

const ROLES = { temp: 'Temperatur', rh: 'Luftfeuchte', vpd: 'VPD', light_level: 'Lampe Stufe', light_on: 'Lampe an/aus',
  exhaust_level: 'Abluft Stufe', heater_switch: 'Heizung', heatmat_switch: 'Heizmatte', room_temp: 'Raum Temperatur', room_rh: 'Raum Feuchte' }
const setups = ref([])
const sensorEdit = ref({})
const hh = ref(null)
const nt = ref(null)
const ntBusy = ref(false)

async function load() {
  const [se, h, n] = await Promise.all([api.get('setups'), api.get('household'), api.get('notify')])
  for (const s of se) sensorEdit.value[s.id] = Object.fromEntries(Object.keys(ROLES).map((k) => [k, s.sensors.find((x) => x.role === k)?.entity_id || '']))
  ;[setups.value, hh.value, nt.value] = [se, h, n]
}
async function saveSensors(id) { await api.put(`setups/${id}/sensors`, sensorEdit.value[id]); say('Sensoren gespeichert') }
async function saveHousehold() {
  hh.value = await api.put('household', { adults: hh.value.adults })
  say('Haushalt gespeichert')
}
async function saveNotify() {
  const keys = ['enabled', 'topic', 'server', 'tasks_enabled', 'tasks_time', 'climate_enabled', 'climate_minutes',
    'climate_strict', 'climate_repeat_hours', 'sensor_offline_minutes']
  try {
    nt.value = await api.put('notify', Object.fromEntries(keys.map((k) => [k, nt.value[k]])))
    say('Push-Einstellungen gespeichert')
  } catch (e) { say(e.message) }
}
async function testNotify(kind) {
  ntBusy.value = true
  try {
    await saveNotify()
    await api.post('notify/test', { kind })
    say('Push gesendet')
  } catch (e) { say(e.message) } finally { ntBusy.value = false }
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1 style="margin-top:8px">Einstellungen</h1>
    </div>

    <details class="panel" open v-if="nt">
      <summary><h2>Push-Benachrichtigungen</h2><span class="small muted">{{ nt.enabled ? 'aktiv' : 'aus' }}</span></summary>
      <div class="stack" style="margin-top:12px">
        <label class="chk"><input type="checkbox" v-model="nt.enabled" /> Push aktiv</label>
        <div class="grid2">
          <label class="field"><span>Topic</span><input v-model="nt.topic" :placeholder="nt.topic_effective || 'z. B. grow_…'" spellcheck="false" autocapitalize="off" /></label>
          <label class="field"><span>Server</span><input v-model="nt.server" :placeholder="nt.server_effective" spellcheck="false" autocapitalize="off" /></label>
        </div>
        <p class="small muted">In der ntfy-App dasselbe Topic abonnieren. Wer das Topic kennt, kann mitlesen – daher keinen leicht zu ratenden Namen wählen.</p>

        <h3>Aufgaben</h3>
        <label class="chk"><input type="checkbox" v-model="nt.tasks_enabled" /> Fällige Aufgaben täglich schicken</label>
        <label class="field" style="max-width:160px"><span>Uhrzeit</span><input type="time" v-model="nt.tasks_time" /></label>

        <h3>Klima-Alarm</h3>
        <label class="chk"><input type="checkbox" v-model="nt.climate_enabled" /> Warnen, wenn Temperatur oder VPD außerhalb des Zielbereichs der Phase liegen</label>
        <div class="grid3">
          <label class="field"><span>Nach (min)</span><input type="number" min="10" max="720" step="10" v-model.number="nt.climate_minutes" /></label>
          <label class="field"><span>Wiederholen nach (h)</span><input type="number" min="1" max="48" v-model.number="nt.climate_repeat_hours" /></label>
          <label class="field"><span>Sensor-Ausfall nach (min)</span><input type="number" min="10" max="720" step="10" v-model.number="nt.sensor_offline_minutes" /></label>
        </div>
        <label class="chk"><input type="checkbox" v-model="nt.climate_strict" /> Streng: schon bei leichter Abweichung warnen</label>
        <p class="small muted">Standard warnt erst bei deutlicher Abweichung (mehr als die halbe Zielspanne daneben). Ohne Pflanze in Sämling, Wachstum oder Blüte gibt es keinen Klima-Alarm.</p>
        <p v-for="a in nt.alarms" :key="a.kind" class="small">Gerade außerhalb: {{ a.kind === 'offline' ? 'Sensor' : a.kind === 'temp' ? 'Temperatur' : 'VPD' }} seit {{ fmt.time(a.since) }}{{ a.alerted ? ', gemeldet' : '' }}</p>

        <div class="row">
          <button @click="saveNotify">Speichern</button>
          <button class="ghost" :disabled="ntBusy || !nt.enabled" @click="testNotify('test')">Test-Push</button>
          <button class="ghost" :disabled="ntBusy || !nt.enabled" @click="testNotify('tasks')">Aufgaben jetzt senden</button>
        </div>
      </div>
    </details>

    <details class="panel" v-if="hh">
      <summary><h2>Haushalt & KCanG</h2><span class="small muted">{{ hh.living_plants }}/{{ hh.plant_limit }} Pflanzen</span></summary>
      <div class="stack" style="margin-top:12px">
        <label class="field"><span>Erwachsene im Haushalt</span><input type="number" min="1" max="10" v-model.number="hh.adults" /></label>
        <p>{{ hh.living_plants }} von {{ hh.plant_limit }} erlaubten lebenden Pflanzen. Zu Hause aufbewahren: bis {{ hh.home_storage_limit_g }} g getrocknet.</p>
        <p class="small muted">3 Pflanzen und 50 g pro volljähriger Person am Wohnsitz; jede Pflanze sollte einer Person zuzuordnen sein. Gezählt werden gesetzte, nicht geerntete Pflanzen. Keine Rechtsberatung.</p>
        <button @click="saveHousehold">Speichern</button>
      </div>
    </details>

    <details class="panel" v-for="s in setups" :key="s.id">
      <summary><h2>Sensoren</h2><span class="small muted">{{ s.name }}</span></summary>
      <div class="stack" style="margin-top:12px">
        <p class="small muted">Entitäten aus Home Assistant. Die App liest nur, sie schaltet nichts.</p>
        <label v-for="(label, role) in ROLES" :key="role" class="field"><span>{{ label }}</span>
          <input v-model="sensorEdit[s.id][role]" placeholder="sensor.…" spellcheck="false" autocapitalize="off" /></label>
        <button @click="saveSensors(s.id)">Speichern</button>
      </div>
    </details>

    <details class="panel">
      <summary><h2>Daten</h2><span class="small muted">Export</span></summary>
      <div class="stack" style="margin-top:12px">
        <a class="btn" href="api/export" download="grow-tagebuch-export.json">Alle Daten exportieren (JSON)</a>
        <p class="small muted">Fotos und Datenbank liegen im Add-on-Ordner und sind Teil der Home-Assistant-Backups.</p>
      </div>
    </details>
  </main>
</template>

<style scoped>
summary { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; cursor: pointer; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary h2 { margin: 0; font-size: 1.05rem; }
summary::after { content: '▾'; color: var(--muted); transition: transform .15s; }
details:not([open]) summary::after { transform: rotate(-90deg); }
summary .muted { margin-left: auto; }
.chk { display: flex; gap: 10px; align-items: flex-start; }
.chk input { width: auto; min-height: auto; margin-top: 4px; flex: none; }
</style>
