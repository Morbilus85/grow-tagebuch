<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, photoUrl } from '../api.js'
import { fmt, LOG_TYPES, rating, say, today } from '../util.js'
import PhaseBar from '../components/PhaseBar.vue'

const route = useRoute()
const router = useRouter()
const s = ref(null)
const logs = ref([])
const edit = ref(false)
const form = ref({})
const big = ref(null)

async function load() {
  const id = route.params.id
  s.value = await api.get(`plants/${id}`)
  logs.value = await api.get(`logs?plant_id=${id}`)
  form.value = { ...s.value.plant }
}
async function save() {
  const f = form.value
  const keys = ['name', 'pot_l', 'pot_height_cm', 'soaked_on', 'planted_on', 'sprouted_on', 'preflower_on', 'flip_on',
    'harvested_on', 'feed_factor', 'mg_deficiency_flag', 'notes', 'status']
  const body = Object.fromEntries(keys.map((k) => [k, f[k] === '' ? null : f[k]]))
  await api.patch(`plants/${s.value.plant.id}`, body)
  edit.value = false
  say('Gespeichert')
  load()
}
async function setDate(field, label) {
  await api.patch(`plants/${s.value.plant.id}`, { [field]: today() })
  await api.post('logs', { plant_id: s.value.plant.id, type: 'phase', text: `${label} am ${fmt.date(today())}` })
  say(`${label} eingetragen`)
  load()
}
async function del(l) {
  if (!confirm(`Eintrag vom ${fmt.dt(l.ts)} löschen?`)) return
  await api.del(`logs/${l.id}`)
  say('Eintrag gelöscht')
  load()
}
async function removePlant() {
  if (!confirm(`${s.value.plant.name} mit allen Einträgen und Fotos löschen?`)) return
  await api.del(`plants/${s.value.plant.id}`)
  router.push('/')
}
function summary(l) {
  const parts = []
  if (l.volume_l) parts.push(`${fmt.n(l.volume_l)} l`)
  if (l.ph_in) parts.push(`pH ${fmt.n(l.ph_in)}`)
  if (l.ec_in) parts.push(`EC ${fmt.n(l.ec_in, 2)}`)
  if (l.ph_runoff) parts.push(`Runoff pH ${fmt.n(l.ph_runoff)}`)
  if (l.height_cm) parts.push(`Höhe ${fmt.n(l.height_cm, 0)} cm`)
  if (l.lamp_distance_cm) parts.push(`Lampe ${fmt.n(l.lamp_distance_cm, 0)} cm`)
  if (l.pot_weight_kg) parts.push(`Topf ${fmt.n(l.pot_weight_kg)} kg`)
  return parts.join(', ')
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="s">
    <div>
      <router-link to="/" class="small muted">Zurück zu Heute</router-link>
      <div class="row between" style="margin-top:8px">
        <div>
          <h1>{{ s.plant.name }}</h1>
          <p class="muted">{{ s.strain?.name }}<template v-if="s.strain?.breeder">, {{ s.strain.breeder }}</template></p>
        </div>
        <div class="day num" v-if="s.phase.day"><small>Tag</small>{{ s.phase.day }}</div>
      </div>
      <span class="chip ok">{{ s.phase.label }}</span>
      <PhaseBar v-if="s.phase.day" :phase="s.phase" :sprouted="s.plant.sprouted_on" />
      <p v-if="s.phase.auto_mapping_note" class="small muted" style="margin-top:8px">{{ s.phase.auto_mapping_note }}</p>
    </div>

    <div class="row">
      <button v-if="!s.plant.planted_on" class="primary" @click="setDate('planted_on', 'Gesetzt')">Heute gesetzt</button>
      <button v-else-if="!s.plant.sprouted_on" class="primary" @click="setDate('sprouted_on', 'Aufgelaufen')">Heute aufgelaufen</button>
      <button v-else-if="!s.plant.preflower_on && s.strain?.auto !== false" @click="setDate('preflower_on', 'Vorblüte')">Vorblüte heute bestätigen</button>
      <button class="ghost" @click="edit = !edit">{{ edit ? 'Schließen' : 'Daten bearbeiten' }}</button>
    </div>

    <form v-if="edit" class="panel stack" @submit.prevent="save">
      <label class="field"><span>Name</span><input v-model="form.name" /></label>
      <div class="grid3">
        <label class="field"><span>Eingeweicht</span><input type="date" v-model="form.soaked_on" /></label>
        <label class="field"><span>Gesetzt</span><input type="date" v-model="form.planted_on" /></label>
        <label class="field"><span>Aufgelaufen</span><input type="date" v-model="form.sprouted_on" /></label>
      </div>
      <div class="grid3">
        <label class="field"><span>Vorblüte bestätigt</span><input type="date" v-model="form.preflower_on" /></label>
        <label class="field"><span>Umstellung 12/12</span><input type="date" v-model="form.flip_on" /></label>
        <label class="field"><span>Geerntet</span><input type="date" v-model="form.harvested_on" /></label>
      </div>
      <div class="grid3">
        <label class="field"><span>Topf (l)</span><input type="number" step="0.5" v-model.number="form.pot_l" /></label>
        <label class="field"><span>Topfhöhe (cm)</span><input type="number" v-model.number="form.pot_height_cm" /></label>
        <label class="field"><span>Düngefaktor</span><input type="number" step="0.05" min="0" max="1.5" v-model.number="form.feed_factor" /></label>
      </div>
      <label class="row"><input type="checkbox" v-model="form.mg_deficiency_flag" style="width:auto;min-height:auto" />
        Magnesium-Mangel beobachtet (CalMag vorziehen)</label>
      <label class="field"><span>Notizen</span><textarea v-model="form.notes"></textarea></label>
      <div class="row between">
        <button type="button" class="danger" @click="removePlant">Pflanze löschen</button>
        <button class="primary">Speichern</button>
      </div>
    </form>

    <div v-if="s.space.height_cm" class="panel stack">
      <h3>Platz bis zur Lampe</h3>
      <div class="grid3">
        <div><p class="small muted">Höhe</p><p class="num" style="font-size:1.4rem">{{ fmt.n(s.space.height_cm, 0) }} cm</p></div>
        <div><p class="small muted">Max. Abstand</p><p class="num" style="font-size:1.4rem">{{ fmt.n(s.space.max_distance_cm, 0) }} cm</p></div>
        <div><p class="small muted">Wachstum</p><p class="num" style="font-size:1.4rem">{{ s.space.growth_cm_per_day ? fmt.n(s.space.growth_cm_per_day) + ' cm/Tag' : '–' }}</p></div>
      </div>
      <p v-for="m in s.space.messages" :key="m" class="note" :class="rating[s.space.status] || 'info'">{{ m }}</p>
    </div>

    <section class="stack">
      <div class="row between">
        <h2>Tagebuch</h2>
        <router-link class="btn primary" :to="{ path: '/eintrag', query: { plant: s.plant.id } }">Neuer Eintrag</router-link>
      </div>
      <p v-if="!logs.length" class="muted">Noch keine Einträge.</p>
      <article v-for="l in logs" :key="l.id" class="entry">
        <div class="row between">
          <div>
            <strong>{{ LOG_TYPES[l.type] || (l.type === 'phase' ? 'Phase' : l.type) }}</strong>&nbsp;
            <span class="small muted">{{ fmt.dt(l.ts) }}</span>
          </div>
          <div class="row">
            <router-link :to="`/eintrag/${l.id}`" class="btn ghost mini">Bearbeiten</router-link>
            <button class="ghost mini" @click="del(l)">Löschen</button>
          </div>
        </div>
        <p v-if="summary(l)" class="num">{{ summary(l) }}</p>
        <p v-if="l.products?.length" class="small">
          <span v-for="p in l.products" :key="p.product_key" class="chip" style="margin:2px 4px 2px 0">
            {{ p.name || p.product_key }} {{ p.amount !== null && p.amount !== undefined ? fmt.n(p.amount) + ' ' + (p.unit || 'ml') : '' }}
          </span>
        </p>
        <p v-if="l.text" style="white-space:pre-wrap">{{ l.text }}</p>
        <div v-if="l.photos.length" class="thumbs">
          <img v-for="ph in l.photos" :key="ph" :src="photoUrl(ph, true)" alt="Foto" @click="big = ph" />
        </div>
      </article>
    </section>

    <div v-if="big" class="lightbox" @click="big = null" role="dialog" aria-label="Foto">
      <img :src="photoUrl(big)" alt="Foto groß" />
    </div>
  </main>
</template>

<style scoped>
.day { font-size: 3.2rem; font-weight: 600; line-height: .9; color: var(--leaf); text-align: right; }
.day small { display: block; font-size: .8rem; color: var(--muted); font-weight: 500; line-height: 1.4; }
.mini { min-height: 34px; padding: 4px 10px; font-size: .875rem; }
.entry { border-left: 3px solid var(--line); padding: 2px 0 10px 12px; }
.entry > * + * { margin-top: 6px; }
.lightbox { position: fixed; inset: 0; z-index: 30; background: rgba(0, 0, 0, .9); display: flex; align-items: center; justify-content: center; }
.lightbox img { max-width: 100%; max-height: 100%; }
.thumbs img { cursor: zoom-in; }
</style>
