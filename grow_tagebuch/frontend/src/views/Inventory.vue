<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { say } from '../util.js'

const products = ref([])
const open = ref(null)
const KIND = { base: 'Grunddünger', stimulant: 'Stimulator', root: 'Wurzel', microbial: 'Bodenleben', carbs: 'Mikrobenfutter',
  amendment: 'Einmischen / Top-Dress', plant_protection: 'Stärkung / Schutz', ph: 'pH', calmag: 'CalMag' }
const groups = computed(() => {
  const g = {}
  for (const p of products.value) (g[p.in_stock ? KIND[p.kind] || p.kind : 'Nicht vorhanden'] ||= []).push(p)
  return g
})
async function load() { products.value = await api.get('products') }
async function save(p) {
  await api.patch(`products/${p.id}`, { in_stock: p.in_stock, label_dose_min: p.label_dose_min, label_dose_max: p.label_dose_max,
    notes: p.notes, effect_group: p.effect_group })
  say(`${p.name} gespeichert`)
  open.value = null
  load()
}
async function toggle(p) { p.in_stock = !p.in_stock; await save(p) }
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <router-link to="/mehr" class="small muted">Zurück</router-link>
    <h1>Inventar</h1>
    <p class="muted">Dosierungen vom Etikett eintragen, damit der Gieß-Assistent konkrete Mengen rechnen kann. Ohne Angabe zeigt er „laut Etikett“.</p>
    <section v-for="(list, name) in groups" :key="name" class="stack">
      <h2>{{ name }}</h2>
      <div v-for="p in list" :key="p.id" class="panel">
        <div class="row between">
          <button class="ghost title" @click="open = open === p.id ? null : p.id" :aria-expanded="open === p.id">
            <strong>{{ p.name }}</strong> <span class="small muted">{{ p.brand }}</span>
          </button>
          <span class="small" :class="p.label_dose_max || p.label_dose_min ? 'muted' : 'warnt'">
            {{ p.label_dose_min || p.label_dose_max ? `${p.label_dose_min ?? '?'}–${p.label_dose_max ?? '?'} ${p.unit}/l` : 'Dosis fehlt' }}
          </span>
        </div>
        <div v-if="open === p.id" class="stack" style="margin-top:12px">
          <div class="grid2">
            <label class="field"><span>Dosis min ({{ p.unit }}/l)</span><input type="number" step="0.05" v-model.number="p.label_dose_min" /></label>
            <label class="field"><span>Dosis max ({{ p.unit }}/l)</span><input type="number" step="0.05" v-model.number="p.label_dose_max" /></label>
          </div>
          <label class="field"><span>Notiz</span><input v-model="p.notes" /></label>
          <div class="row between">
            <button class="ghost" @click="toggle(p)">{{ p.in_stock ? 'Als nicht vorhanden markieren' : 'Als vorhanden markieren' }}</button>
            <button class="primary" @click="save(p)">Speichern</button>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.title { border: 0; padding: 0; min-height: 0; text-align: left; justify-content: flex-start; }
.warnt { color: var(--amber); }
</style>
