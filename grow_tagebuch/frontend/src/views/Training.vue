<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { say, TRAINING } from '../util.js'

const list = ref([])
const filter = ref('alle')
const form = ref(null)

const groups = computed(() => {
  const g = {}
  for (const t of list.value) {
    if (filter.value === 'auto' && t.auto === 'abraten') continue
    if (filter.value === 'photo' && t.photo === 'abraten') continue
    ;(g[t.category] ||= []).push(t)
  }
  return Object.keys(TRAINING.category).filter((k) => g[k]).map((k) => [k, g[k]])
})
async function load() { list.value = await api.get('training') }
function startForm() {
  form.value = { name: '', aka: '', category: 'lst', stress: 'niedrig', auto: 'bedingt', photo: 'bedingt', summary: '', when: '', stepsText: '', recovery_days: 0 }
}
async function create() {
  const f = form.value
  await api.post('training', { ...f, steps: f.stepsText.split('\n').map((s) => s.trim()).filter(Boolean) })
  say(`${f.name} angelegt`)
  form.value = null
  load()
}
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <router-link to="/mehr" class="small muted">Zurück</router-link>
    <div class="row between">
      <h1>Training</h1>
      <button class="ghost" @click="startForm">Eigene Technik</button>
    </div>
    <p class="muted">Welche Technik gerade zu deiner Pflanze passt, siehst du direkt bei der Pflanze. Hier findest du alle Anleitungen.</p>

    <div class="row" role="group" aria-label="Filter">
      <button v-for="[k, l] in [['alle', 'Alle'], ['auto', 'Für Autos'], ['photo', 'Für Photos']]" :key="k"
              :class="{ primary: filter === k }" @click="filter = k">{{ l }}</button>
    </div>

    <form v-if="form" class="panel stack" @submit.prevent="create">
      <h3>Eigene Technik</h3>
      <div class="grid2">
        <label class="field"><span>Name</span><input v-model="form.name" required /></label>
        <label class="field"><span>Auch bekannt als</span><input v-model="form.aka" /></label>
        <label class="field"><span>Art</span><select v-model="form.category"><option v-for="(l, k) in TRAINING.category" :key="k" :value="k">{{ l }}</option></select></label>
        <label class="field"><span>Stress</span><select v-model="form.stress"><option v-for="(l, k) in TRAINING.stress" :key="k" :value="k">{{ l }}</option></select></label>
        <label class="field"><span>Autos</span><select v-model="form.auto"><option v-for="(l, k) in TRAINING.suit" :key="k" :value="k">{{ l }}</option></select></label>
        <label class="field"><span>Photos</span><select v-model="form.photo"><option v-for="(l, k) in TRAINING.suit" :key="k" :value="k">{{ l }}</option></select></label>
      </div>
      <label class="field"><span>Kurzbeschreibung</span><textarea v-model="form.summary"></textarea></label>
      <label class="field"><span>Wann</span><input v-model="form.when" /></label>
      <label class="field"><span>Schritte (einer pro Zeile)</span><textarea v-model="form.stepsText"></textarea></label>
      <div class="row between"><button type="button" class="ghost" @click="form = null">Abbrechen</button><button class="primary">Technik anlegen</button></div>
    </form>

    <section v-for="[cat, items] in groups" :key="cat" class="stack">
      <h2>{{ TRAINING.category[cat] }}</h2>
      <router-link v-for="t in items" :key="t.key" :to="`/training/${t.key}`" class="panel tech">
        <div class="row between">
          <h3>{{ t.name }}</h3>
          <span class="small muted">{{ TRAINING.stress[t.stress] }}</span>
        </div>
        <p class="small muted" v-if="t.aka">{{ t.aka }}</p>
        <p class="small">{{ t.goal || t.summary }}</p>
        <div class="row">
          <span class="chip" :class="TRAINING.suitClass[t.auto]">Autos: {{ TRAINING.suit[t.auto] }}</span>
          <span class="chip" :class="TRAINING.suitClass[t.photo]">Photos: {{ TRAINING.suit[t.photo] }}</span>
        </div>
      </router-link>
    </section>
  </main>
</template>

<style scoped>
.tech { display: block; text-decoration: none; }
.tech > * + * { margin-top: 6px; }
</style>
