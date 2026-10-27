<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { say, TRAINING } from '../util.js'

const route = useRoute()
const router = useRouter()
const t = ref(null)
const all = ref({})
const notes = ref('')
const plantId = computed(() => Number(route.query.plant) || null)

async function load() {
  t.value = await api.get(`training/${route.params.key}`)
  notes.value = t.value.my_notes
  if (!Object.keys(all.value).length) all.value = Object.fromEntries((await api.get('training')).map((x) => [x.key, x]))
}
async function saveNotes() {
  await api.patch(`training/${t.value.key}`, { my_notes: notes.value })
  say('Notiz gespeichert')
}
async function remove() {
  if (!confirm(`${t.value.name} löschen?`)) return
  await api.del(`training/${t.value.key}`)
  router.push('/training')
}
watch(() => route.params.key, load)
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="t">
    <router-link :to="plantId ? `/pflanze/${plantId}` : '/training'" class="small muted">{{ plantId ? 'Zurück zur Pflanze' : 'Alle Techniken' }}</router-link>
    <div>
      <h1>{{ t.name }}</h1>
      <p class="muted" v-if="t.aka">{{ t.aka }}</p>
      <div class="row" style="margin-top:8px">
        <span class="chip">{{ TRAINING.category[t.category] }}</span>
        <span class="chip">{{ TRAINING.stress[t.stress] }}</span>
        <span class="chip" :class="TRAINING.suitClass[t.auto]">Autos: {{ TRAINING.suit[t.auto] }}</span>
        <span class="chip" :class="TRAINING.suitClass[t.photo]">Photos: {{ TRAINING.suit[t.photo] }}</span>
      </div>
    </div>

    <p class="lead">{{ t.summary }}</p>
    <div class="stack">
      <p v-if="t.goal"><strong>Ziel:</strong> {{ t.goal }}</p>
      <p v-if="t.when"><strong>Wann:</strong> {{ t.when }}</p>
      <p v-if="t.recovery_days"><strong>Erholung:</strong> etwa {{ t.recovery_days }} Tage, in der Zeit kein weiteres belastendes Training.</p>
    </div>
    <p v-if="t.auto_note" class="note info"><strong>Bei Autos:</strong> {{ t.auto_note }}</p>

    <section v-if="t.steps?.length" class="stack">
      <h2>So geht's</h2>
      <ol class="steps"><li v-for="s in t.steps" :key="s">{{ s }}</li></ol>
    </section>

    <section v-if="t.mistakes?.length" class="stack">
      <h2>Typische Fehler</h2>
      <ul><li v-for="m in t.mistakes" :key="m">{{ m }}</li></ul>
    </section>

    <section v-if="t.tools?.length" class="stack">
      <h3>Material</h3>
      <p>{{ t.tools.join(', ') }}</p>
    </section>

    <section v-if="t.combines_with?.length" class="stack">
      <h3>Passt gut zusammen mit</h3>
      <div class="row">
        <router-link v-for="k in t.combines_with" :key="k" :to="{ path: `/training/${k}`, query: route.query }" class="chip">{{ all[k]?.name || k }}</router-link>
      </div>
    </section>

    <router-link v-if="plantId" class="btn primary" :to="{ path: '/eintrag', query: { plant: plantId, type: t.category === 'schnitt' ? 'defoliation' : 'training', technique: t.key, photo: 1 } }">
      Als durchgeführt eintragen
    </router-link>

    <section class="panel stack">
      <h3>Meine Notizen</h3>
      <textarea v-model="notes" placeholder="Erfahrungen, was bei dir funktioniert hat …"></textarea>
      <div class="row between">
        <button v-if="!t.builtin" class="danger" @click="remove">Technik löschen</button><span v-else></span>
        <button @click="saveNotes">Notiz speichern</button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.lead { font-size: 1.1rem; }
.steps { padding-left: 22px; }
.steps li { margin: 8px 0; padding-left: 4px; }
ul { padding-left: 20px; }
ul li { margin: 6px 0; }
</style>
