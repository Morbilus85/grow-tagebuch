<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, photoUrl } from '../api.js'
import { LOG_TYPES, say, shrinkImage } from '../util.js'

const route = useRoute()
const router = useRouter()
const editId = computed(() => route.params.id)
const plants = ref([])
const products = ref([])
const techniques = ref([])
const f = ref({ type: route.query.type || 'observation', plant_id: Number(route.query.plant) || null, text: '', products: [], technique_key: route.query.technique || null })
const files = ref([])
const existingPhotos = ref([])
const fileInput = ref(null)
const busy = ref(false)

const has = (...t) => t.includes(f.value.type)
const productList = computed(() => products.value.filter((p) => p.in_stock))
const ts = ref('')

async function load() {
  const t = await api.get('today')
  plants.value = t.runs.flatMap((r) => r.plants.map((s) => ({ ...s.plant, runName: r.run.name })))
  products.value = await api.get('products')
  techniques.value = await api.get('training')
  if (editId.value) {
    const l = await api.get(`logs/${editId.value}`)
    f.value = { ...l, products: l.products || [] }
    existingPhotos.value = l.photos
    ts.value = l.ts.slice(0, 16)
  } else {
    const now = new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    ts.value = now.toISOString().slice(0, 16)
    if (!f.value.plant_id && plants.value.length === 1) f.value.plant_id = plants.value[0].id
    if (route.query.photo) setTimeout(() => fileInput.value?.click(), 300)
  }
}
function onFiles(e) { files.value = [...files.value, ...e.target.files] }
function addProduct() { f.value.products.push({ product_key: productList.value[0]?.key, amount: null, unit: productList.value[0]?.unit || 'ml' }) }
function syncUnit(p) {
  const prod = products.value.find((x) => x.key === p.product_key)
  if (prod) { p.unit = prod.unit; p.name = prod.name }
}
async function save() {
  if (!f.value.plant_id) { say('Bitte eine Pflanze wählen'); return }
  busy.value = true
  try {
    const body = { ...f.value, ts: ts.value ? ts.value + ':00' : undefined }
    body.products = (body.products || []).filter((p) => p.product_key).map((p) => { syncUnit(p); return p })
    delete body.photos
    const l = editId.value ? await api.patch(`logs/${editId.value}`, body) : await api.post('logs', body)
    const failed = []
    for (const file of files.value) {
      try { await api.upload(`logs/${l.id}/photos`, await shrinkImage(file)) } catch (e) { failed.push(`${file.name}: ${e.message}`) }
    }
    files.value = []
    if (failed.length) {
      say(`Eintrag gespeichert, aber ${failed.length} Foto(s) nicht: ${failed[0]}`)
      router.replace(`/eintrag/${l.id}`)
      return
    }
    say(editId.value ? 'Eintrag gespeichert' : 'Eintrag angelegt')
    router.push(`/pflanze/${f.value.plant_id}`)
  } catch (e) { say(e.message) } finally { busy.value = false }
}
async function delPhoto(id) {
  if (!confirm('Foto löschen?')) return
  await api.del(`photos/${id}`)
  existingPhotos.value = existingPhotos.value.filter((x) => x !== id)
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <h1>{{ editId ? 'Eintrag bearbeiten' : 'Neuer Eintrag' }}</h1>
    <form class="stack" @submit.prevent="save">
      <div class="grid2">
        <label class="field"><span>Pflanze</span>
          <select v-model.number="f.plant_id" required>
            <option :value="null" disabled>Wählen</option>
            <option v-for="p in plants" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </label>
        <label class="field"><span>Art</span>
          <select v-model="f.type"><option v-for="(l, k) in LOG_TYPES" :key="k" :value="k" v-show="!['pest', 'treatment'].includes(k) || f.type === k">{{ l }}</option></select>
        </label>
      </div>
      <label class="field"><span>Zeitpunkt</span><input type="datetime-local" v-model="ts" /></label>

      <label v-if="has('training', 'defoliation')" class="field"><span>Technik</span>
        <select v-model="f.technique_key">
          <option :value="null">Keine Angabe</option>
          <option v-for="t in techniques" :key="t.key" :value="t.key">{{ t.name }}</option>
        </select>
      </label>
      <div v-if="has('measurement')" class="grid2">
        <label class="field"><span>Höhe Pflanze (cm)</span><input type="number" step="1" inputmode="numeric" v-model.number="f.height_cm" /></label>
        <label class="field"><span>Nodien am Haupttrieb</span><input type="number" step="1" min="0" inputmode="numeric" v-model.number="f.nodes" /></label>
        <label class="field"><span>Abstand Lampe (cm)</span><input type="number" step="1" inputmode="numeric" v-model.number="f.lamp_distance_cm" /></label>
        <label class="field"><span>Topfgewicht (kg)</span><input type="number" step="any" inputmode="decimal" v-model.number="f.pot_weight_kg" /></label>
      </div>
      <p v-if="has('measurement')" class="small muted">Höhe ab Erdoberfläche bis zur Spitze. Abstand von der Lampen-Unterkante bis zur Spitze. Nodien: Stellen am Haupttrieb, an denen sich Blätter und Seitentriebe gegenüberstehen – die Keimblätter nicht mitzählen.</p>

      <template v-if="has('watering', 'feeding', 'top_dress', 'foliar')">
        <div class="grid3" v-if="has('watering', 'feeding')">
          <label class="field"><span>Menge (l)</span><input type="number" step="any" min="0" inputmode="decimal" placeholder="z. B. 0,035" v-model.number="f.volume_l" /></label>
          <label class="field"><span>pH</span><input type="number" step="any" inputmode="decimal" v-model.number="f.ph_in" /></label>
          <label class="field"><span>EC</span><input type="number" step="any" inputmode="decimal" v-model.number="f.ec_in" /></label>
        </div>
        <div class="grid3" v-if="has('watering', 'feeding')">
          <label class="field"><span>Runoff (l)</span><input type="number" step="any" inputmode="decimal" v-model.number="f.runoff_l" /></label>
          <label class="field"><span>pH Runoff</span><input type="number" step="any" inputmode="decimal" v-model.number="f.ph_runoff" /></label>
          <label class="field"><span>EC Runoff</span><input type="number" step="any" inputmode="decimal" v-model.number="f.ec_runoff" /></label>
        </div>
        <div class="stack">
          <div class="row between"><span class="small muted">Produkte</span><button type="button" class="ghost" @click="addProduct">Produkt hinzufügen</button></div>
          <div v-for="(p, i) in f.products" :key="i" class="prod">
            <select v-model="p.product_key" @change="syncUnit(p)"><option v-for="x in productList" :key="x.key" :value="x.key">{{ x.name }}</option></select>
            <input type="number" step="any" inputmode="decimal" v-model.number="p.amount" placeholder="Menge" />
            <span class="muted">{{ p.unit }}</span>
            <button type="button" class="ghost" @click="f.products.splice(i, 1)" aria-label="Entfernen">✕</button>
          </div>
        </div>
      </template>

      <label v-if="has('problem', 'pest')" class="field"><span>Schweregrad</span>
        <select v-model.number="f.severity"><option :value="1">leicht</option><option :value="2">mittel</option><option :value="3">stark</option></select>
      </label>
      <p v-if="!editId" class="small muted">Schädlinge oder Krankheiten? <router-link :to="{ path: '/schaedlinge', query: { neu: 1, plant: f.plant_id } }">Als Befall melden</router-link> – dann gilt er fürs ganze Zelt oder ausgewählte Pflanzen und hat einen eigenen Verlauf.</p>
      <p v-if="has('pest')" class="small muted">Was hast du gefunden (z. B. Trauermücken auf der Gelbtafel, Gespinste, Fraßspuren)? Ein Foto hilft später bei der Auswertung.</p>

      <label class="field"><span>Notiz</span><textarea v-model="f.text"></textarea></label>

      <div class="stack">
        <div class="row between">
          <span class="small muted">Fotos</span>
          <button type="button" @click="fileInput.click()">Foto aufnehmen oder wählen</button>
        </div>
        <input ref="fileInput" type="file" accept="image/*" multiple hidden @change="onFiles" />
        <div class="thumbs" v-if="existingPhotos.length || files.length">
          <img v-for="ph in existingPhotos" :key="ph" :src="photoUrl(ph, true)" alt="Foto" @click="delPhoto(ph)" title="Antippen zum Löschen" />
          <span v-for="(file, i) in files" :key="'n' + i" class="newfile small">{{ file.name }} (wird beim Speichern hochgeladen)</span>
        </div>
      </div>

      <button class="primary" :disabled="busy">{{ busy ? 'Speichert …' : 'Speichern' }}</button>
    </form>
  </main>
</template>

<style scoped>
.prod { display: grid; grid-template-columns: 1fr 96px 36px 44px; gap: 6px; align-items: center; }
.newfile { background: var(--sunken); border-radius: 8px; padding: 8px; overflow: hidden; text-overflow: ellipsis; aspect-ratio: 1; display: flex; align-items: center; }
</style>
