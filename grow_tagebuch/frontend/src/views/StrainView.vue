<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api.js'
import { say } from '../util.js'
import StrainInfo from '../components/StrainInfo.vue'

const route = useRoute()
const s = ref(null)
const edit = ref(null)
const busy = ref(false)
const err = ref('')

async function load() { s.value = await api.get(`strains/${route.params.id}`) }
async function refresh() {
  busy.value = true
  err.value = ''
  try {
    s.value = await api.post(`strains/${s.value.id}/refresh`)
    say('Steckbrief aktualisiert')
  } catch (e) { err.value = e.message } finally { busy.value = false }
}
function startEdit() {
  const x = s.value
  edit.value = { name: x.name, breeder: x.breeder, auto: x.auto, seed_to_harvest_days: x.seed_to_harvest_days, flowering_days: x.flowering_days,
    max_height_cm: x.max_height_cm, genetics: x.genetics, notes: x.notes }
}
async function save() {
  s.value = await api.patch(`strains/${s.value.id}`, edit.value)
  edit.value = null
  say('Gespeichert')
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="s">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1 style="margin-top:8px">{{ s.name }}</h1>
      <p class="muted">{{ s.breeder }}<template v-if="s.plants"> · {{ s.plants }} Pflanzen im Tagebuch</template></p>
    </div>

    <section class="panel">
      <StrainInfo :strain="s" />
      <p v-if="!Object.keys(s.info).length" class="small muted" style="margin-top:12px">Noch kein Steckbrief. Die Trainings-Einschätzung oben ist die allgemeine für {{ s.auto ? 'Autoflower' : 'Photos' }}.</p>
    </section>

    <p v-if="s.notes" class="note info">{{ s.notes }}</p>

    <div class="stack">
      <div class="row">
        <button class="primary" :disabled="busy || !s.lookup_available" @click="refresh">{{ busy ? 'Recherchiere … (bis zu 1 Minute)' : 'Infos aus dem Internet holen' }}</button>
        <button class="ghost" @click="edit ? (edit = null) : startEdit()">{{ edit ? 'Schließen' : 'Bearbeiten' }}</button>
      </div>
      <p v-if="!s.lookup_available" class="small muted">Für den Internet-Abruf wird ein Claude-API-Schlüssel gebraucht: Home Assistant → Einstellungen → Add-ons → Grow-Tagebuch → Konfiguration → anthropic_api_key.</p>
      <p v-if="err" class="note bad">{{ err }}</p>
    </div>

    <form v-if="edit" class="panel stack" @submit.prevent="save">
      <div class="grid2">
        <label class="field"><span>Sorte</span><input v-model="edit.name" required /></label>
        <label class="field"><span>Breeder</span><input v-model="edit.breeder" /></label>
        <label class="field"><span>Typ</span><select v-model="edit.auto"><option :value="true">Autoflower</option><option :value="false">Photoperiodisch</option></select></label>
        <label class="field" v-if="edit.auto"><span>Samen bis Ernte (Tage)</span><input type="number" v-model.number="edit.seed_to_harvest_days" /></label>
        <label class="field" v-else><span>Blütedauer (Tage)</span><input type="number" v-model.number="edit.flowering_days" /></label>
        <label class="field"><span>Max. Höhe (cm)</span><input type="number" v-model.number="edit.max_height_cm" /></label>
        <label class="field"><span>Genetik</span><input v-model="edit.genetics" /></label>
      </div>
      <label class="field"><span>Notizen</span><textarea v-model="edit.notes"></textarea></label>
      <p class="small muted">„Samen bis Ernte“ steuert die Phasen (Vorblüte, Erntefenster) aller Pflanzen dieser Sorte.</p>
      <button class="primary">Speichern</button>
    </form>
  </main>
</template>
