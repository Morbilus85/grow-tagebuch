<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, photoUrl } from '../api.js'
import { fmt, say, shrinkImage } from '../util.js'

// Start eines KI-Gesprächs: /ki/neu?pflanze=<id>&art=check|frage oder /ki/neu?zelt=<setup_id>
const route = useRoute()
const router = useRouter()
const plantId = Number(route.query.pflanze) || null
const setupId = Number(route.query.zelt) || null
const kind = ref(plantId && route.query.art !== 'frage' ? 'check' : 'frage')
const title = ref('')
const text = ref('')
const photos = ref([]) // {id, ts}
const selected = ref([])
const files = ref([])
const busy = ref(false)
const aiOk = ref(true)

const WEEK = 7 * 864e5
const recent = computed(() => photos.value.filter((p) => Date.now() - new Date(p.ts) < WEEK))

async function load() {
  aiOk.value = (await api.get('ai/status')).available
  if (plantId) {
    const s = await api.get(`plants/${plantId}`)
    title.value = s.plant.name
    const logs = await api.get(`logs?plant_id=${plantId}&limit=60`)
    photos.value = logs.flatMap((l) => l.photos.map((id) => ({ id, ts: l.ts }))).sort((a, b) => b.id - a.id)
    selected.value = recent.value.slice(0, 3).map((p) => p.id)
  } else if (setupId) {
    const se = (await api.get('setups')).find((x) => x.id === setupId)
    title.value = se ? `Zelt ${se.name}` : 'Zelt'
  }
}
function toggle(id) {
  const i = selected.value.indexOf(id)
  if (i >= 0) selected.value.splice(i, 1)
  else if (selected.value.length + files.value.length < 4) selected.value.push(id)
  else say('Höchstens 4 Fotos pro Check')
}
// Einzeln wählen (kein `multiple`, HA-Android-App liefert sonst eine leere Liste)
function onFile(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) { say('Kein Foto übernommen – bitte noch einmal wählen'); return }
  if (selected.value.length + files.value.length >= 4) { say('Höchstens 4 Fotos pro Check'); return }
  files.value.push({ file: f, url: URL.createObjectURL(f) })
}
function dropFile(i) { URL.revokeObjectURL(files.value[i].url); files.value.splice(i, 1) }

async function start() {
  if (kind.value === 'frage' && !text.value.trim()) { say('Bitte eine Frage eingeben'); return }
  busy.value = true
  try {
    const ids = [...selected.value]
    if (files.value.length) {
      const s = await api.get(`plants/${plantId}`)
      const l = await api.post('logs', { plant_id: plantId, run_id: s.plant.run_id, type: 'observation',
        text: `Foto für KI-${kind.value === 'check' ? 'Check' : 'Frage'}` })
      for (const { file } of files.value) ids.push((await api.upload(`logs/${l.id}/photos`, await shrinkImage(file))).id)
    }
    if (kind.value === 'check' && !ids.length && !confirm('Keine aktuellen Fotos ausgewählt. Die KI wird dann zuerst Fotos anfordern. Trotzdem starten?')) return
    const body = { kind: kind.value, text: text.value, photo_ids: ids }
    if (plantId) body.plant_id = plantId
    else body.setup_id = setupId
    const chat = await api.post('ai/chats', body)
    router.replace(`/ki/${chat.id}`)
  } catch (e) { say(e.message) } finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <div>
      <a href="#" class="small muted" @click.prevent="router.back()">Zurück</a>
      <h1 style="margin-top:8px">{{ kind === 'check' ? 'Begutachten' : 'KI fragen' }}</h1>
      <p class="muted">{{ title }}</p>
    </div>

    <p v-if="!aiOk" class="note bad">Kein Claude-API-Schlüssel hinterlegt (Add-on → Konfiguration).</p>

    <div v-if="plantId" class="row" role="group" aria-label="Art">
      <button class="chip" :class="{ ok: kind === 'check' }" @click="kind = 'check'">Pflanze begutachten</button>
      <button class="chip" :class="{ ok: kind === 'frage' }" @click="kind = 'frage'">Nur Frage stellen</button>
    </div>

    <section v-if="plantId" class="panel stack">
      <h3>Fotos</h3>
      <p class="small muted" v-if="kind === 'check'">Die neuesten Fotos der letzten 7 Tage sind vorausgewählt (max. 4). Antippen wählt ab oder zu.</p>
      <p class="small muted" v-else>Optional – für eine reine Frage braucht es kein Foto.</p>
      <div class="thumbs" v-if="photos.length || files.length">
        <button v-for="p in photos.slice(0, 12)" :key="p.id" class="pick" :class="{ on: selected.includes(p.id) }" @click="toggle(p.id)"
                :aria-pressed="selected.includes(p.id)" :title="fmt.dt(p.ts)">
          <img :src="photoUrl(p.id, true)" :alt="`Foto vom ${fmt.dt(p.ts)}`" />
          <span class="small">{{ fmt.date(p.ts) }}</span>
        </button>
        <button v-for="(nf, i) in files" :key="'n' + i" class="pick on" @click="dropFile(i)" title="Antippen zum Entfernen">
          <img :src="nf.url" alt="Neues Foto" /><span class="small">neu</span>
        </button>
      </div>
      <label class="btn filebtn">Neues Foto aufnehmen<input type="file" accept="image/*" @change="onFile" /></label>
      <p class="small muted">Tipp gegen den LED-Farbstich: ein weißes Blatt Papier mit ins Bild halten oder Lampe runterdimmen und
        Handylicht an. Für Blätter nah ran, scharf, auch mal die Unterseite.</p>
    </section>

    <label class="field">
      <span>{{ kind === 'check' ? 'Was fällt dir auf? (optional)' : 'Deine Frage' }}</span>
      <textarea v-model="text" rows="3" :placeholder="kind === 'check' ? 'z. B. Blattspitzen werden braun' : (plantId ? 'z. B. Wann sollte ich das nächste Mal gießen?' : 'z. B. Passt das Klima nachts?')"></textarea>
    </label>

    <div class="row between">
      <span class="small muted">Opus, ca. 10–20 Cent pro Check, Rückfragen wenige Cent</span>
      <button class="primary" :disabled="busy || !aiOk" @click="start">{{ busy ? 'Wird gestartet …' : (kind === 'check' ? 'Begutachten' : 'Fragen') }}</button>
    </div>
  </main>
</template>

<style scoped>
.pick { padding: 0; border: 2px solid transparent; border-radius: 10px; background: none; opacity: .55; display: flex; flex-direction: column; gap: 2px; min-height: auto; }
.pick.on { border-color: var(--leaf); opacity: 1; }
.pick span { text-align: center; color: var(--muted); }
.filebtn { position: relative; overflow: hidden; cursor: pointer; }
.filebtn input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
</style>
