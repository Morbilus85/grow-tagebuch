<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, photoUrl } from '../api.js'
import { fmt, PEST, say, shrinkImage } from '../util.js'

const route = useRoute()
const router = useRouter()
const c = ref(null)
const finding = ref({ text: '', severity: null })
const findingFile = ref(null)
const openT = ref(null)
const tNote = ref('')
const editScope = ref(false)
const big = ref(null)
const PH = { seedling: 'Sämling/Keimung', keimung: 'Keimung', einweichen: 'Keimung', veg: 'Wachstum', bloom: 'Blüte', flush: 'Reife' }

async function load() { c.value = await api.get(`pests/cases/${route.params.id}`) }
async function patch(body, msg) { c.value = await api.patch(`pests/cases/${c.value.id}`, body); if (msg) say(msg) }
async function addFinding() {
  if (!finding.value.text && !findingFile.value) return
  const l = await api.post(`pests/cases/${c.value.id}/finding`, { text: finding.value.text, severity: finding.value.severity })
  if (findingFile.value) {
    try { await api.upload(`logs/${l.id}/photos`, await shrinkImage(findingFile.value)) } catch (e) { say(`Foto fehlgeschlagen: ${e.message}`) }
  }
  finding.value = { text: '', severity: null }
  findingFile.value = null
  say('Befund eingetragen')
  load()
}
async function doTreatment(t) {
  const r = await api.post(`pests/cases/${c.value.id}/treatment`, { treatment_key: t.key, text: tNote.value })
  say(r.follow_ups.length ? `Eingetragen – Folgetermin(e): ${r.follow_ups.map(fmt.date).join(', ')}` : 'Maßnahme eingetragen')
  openT.value = null
  tNote.value = ''
  load()
}
async function remove() {
  if (!confirm(`Befall „${c.value.name}“ samt Verlauf löschen?`)) return
  await api.del(`pests/cases/${c.value.id}`)
  router.push('/schaedlinge')
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="c">
    <router-link to="/schaedlinge" class="small muted">Alle Befälle</router-link>
    <div>
      <div class="row between">
        <h1>{{ c.name }}</h1>
        <span class="chip" :class="PEST.statusClass[c.status]">{{ PEST.status[c.status] }}</span>
      </div>
      <p class="muted">{{ PEST.scope(c, c.plants) }}, {{ PEST.severity[c.severity] }}, seit {{ fmt.date(c.started_on) }}
        <button class="ghost mini" @click="editScope = !editScope">ändern</button></p>
    </div>

    <div v-if="editScope" class="panel stack">
      <div class="row">
        <button :class="{ primary: c.scope === 'zelt' }" @click="patch({ scope: 'zelt' })">Ganzes Zelt</button>
        <button :class="{ primary: c.scope === 'pflanzen' }" @click="patch({ scope: 'pflanzen', plant_ids: c.plant_ids.length ? c.plant_ids : [c.plants[0]?.id] })">Einzelne Pflanzen</button>
      </div>
      <div v-if="c.scope === 'pflanzen'" class="row">
        <label v-for="p in c.plants" :key="p.id" class="row chipbox">
          <input type="checkbox" :checked="c.plant_ids.includes(p.id)"
                 @change="patch({ plant_ids: $event.target.checked ? [...c.plant_ids, p.id] : c.plant_ids.filter((x) => x !== p.id) })" /> {{ p.name }}
        </label>
      </div>
      <label class="field"><span>Stärke</span>
        <select :value="c.severity" @change="patch({ severity: Number($event.target.value) })"><option v-for="(l, k) in PEST.severity" :key="k" :value="Number(k)">{{ l }}</option></select>
      </label>
    </div>

    <div class="row">
      <button v-if="c.status !== 'erledigt'" class="primary" @click="patch({ status: 'erledigt' }, 'Befall als erledigt markiert – Folgetermine entfernt')">Erledigt</button>
      <button v-else @click="patch({ status: 'behandlung' }, 'Befall wieder geöffnet')">Wieder öffnen</button>
    </div>

    <section v-if="c.treatments.length" class="stack">
      <h2>Maßnahmen</h2>
      <p class="small muted">Bewertet für die Phase {{ PH[c.phase] || c.phase }}<template v-if="c.bloom_week"> (Woche {{ c.bloom_week }})</template> der betroffenen Pflanzen.</p>
      <article v-for="t in c.treatments" :key="t.key" class="treat" :class="{ blocked: !t.allowed }">
        <button class="ghost head" @click="openT = openT === t.key ? null : t.key" :aria-expanded="openT === t.key">
          <strong>{{ t.name }}</strong>
          <span class="chip" :class="t.allowed ? 'ok' : 'bad'">{{ t.allowed ? 'möglich' : 'gesperrt' }}</span>
        </button>
        <p v-if="t.blocked_reason" class="small" style="color:var(--alarm)">{{ t.blocked_reason }}</p>
        <p v-if="t.note" class="small muted">{{ t.note }}</p>
        <div v-if="openT === t.key" class="stack" style="margin-top:8px">
          <ol class="steps small"><li v-for="s in t.how" :key="s">{{ s }}</li></ol>
          <p v-if="t.repeat" class="small">Wiederholung: insgesamt {{ t.repeat.times }}×, alle {{ t.repeat.interval_days }} Tage. Die Folgetermine landen als Aufgaben auf „Heute“.</p>
          <template v-if="t.allowed && c.status !== 'erledigt'">
            <input v-model="tNote" placeholder="Notiz (optional), z. B. Menge, Produkt" />
            <button class="primary" @click="doTreatment(t)">Heute durchgeführt</button>
          </template>
        </div>
      </article>
    </section>

    <section class="panel stack" v-if="c.status !== 'erledigt'">
      <h3>Befund eintragen</h3>
      <textarea v-model="finding.text" placeholder="z. B. Gelbtafel: 3 Mücken, deutlich weniger als letzte Woche"></textarea>
      <div class="grid2">
        <label class="field"><span>Stärke jetzt</span>
          <select v-model.number="finding.severity"><option :value="null">unverändert</option><option v-for="(l, k) in PEST.severity" :key="k" :value="Number(k)">{{ l }}</option></select>
        </label>
        <label class="field"><span>Foto</span><input type="file" accept="image/*" @change="findingFile = $event.target.files[0]" /></label>
      </div>
      <button @click="addFinding">Befund speichern</button>
    </section>

    <section class="stack">
      <h2>Verlauf</h2>
      <div v-if="c.tasks.length" class="stack">
        <p v-for="t in c.tasks" :key="t.id" class="note warn small">Geplant {{ fmt.date(t.due_on) }}: {{ t.title }}</p>
      </div>
      <article v-for="l in c.logs" :key="l.id" class="entry">
        <p><strong>{{ l.type === 'treatment' ? 'Maßnahme' : 'Befund' }}</strong> <span class="small muted">{{ fmt.dt(l.ts) }}</span>
          <span v-if="l.severity" class="small muted">, {{ PEST.severity[l.severity] }}</span></p>
        <p v-if="l.text" style="white-space:pre-wrap">{{ l.text }}</p>
        <div v-if="l.photos.length" class="thumbs"><img v-for="ph in l.photos" :key="ph" :src="photoUrl(ph, true)" alt="Foto" @click="big = ph" /></div>
      </article>
    </section>

    <section class="stack">
      <h2>Wissen</h2>
      <div v-if="c.pest.signs.length"><h3>Erkennen</h3><ul><li v-for="s in c.pest.signs" :key="s">{{ s }}</li></ul></div>
      <p v-if="c.pest.causes"><strong>Ursachen:</strong> {{ c.pest.causes }}</p>
      <div v-if="c.pest.prevention.length"><h3>Vorbeugen</h3><ul><li v-for="s in c.pest.prevention" :key="s">{{ s }}</li></ul></div>
    </section>

    <button class="danger" @click="remove">Befall löschen</button>

    <div v-if="big" class="lightbox" @click="big = null"><img :src="photoUrl(big)" alt="Foto groß" /></div>
  </main>
</template>

<style scoped>
.mini { min-height: 32px; padding: 2px 10px; font-size: .875rem; }
.chipbox { background: var(--sunken); border-radius: 999px; padding: 6px 12px; }
.treat { border-left: 3px solid var(--leaf); padding: 2px 0 8px 12px; }
.treat.blocked { border-color: var(--alarm); opacity: .8; }
.treat .head { width: 100%; justify-content: space-between; border: 0; padding: 4px 0; min-height: 0; background: transparent; }
.steps { padding-left: 22px; }
.steps li { margin: 4px 0; }
ul { padding-left: 20px; }
.entry { border-left: 3px solid var(--line); padding: 2px 0 8px 12px; }
.entry > * + * { margin-top: 4px; }
.lightbox { position: fixed; inset: 0; z-index: 30; background: rgba(0, 0, 0, .9); display: flex; align-items: center; justify-content: center; }
.lightbox img { max-width: 100%; max-height: 100%; }
</style>
