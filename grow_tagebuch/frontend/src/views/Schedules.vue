<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt } from '../util.js'

const schedules = ref([])
const products = ref({})
const STAGES = ['seedling', 'veg', 'bloom_1', 'bloom_2', 'bloom_3', 'bloom_4', 'bloom_5', 'bloom_6', 'bloom_7', 'bloom_8']
const HEAD = ['Anzucht', 'Wachs.', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8']
onMounted(async () => {
  schedules.value = await api.get('schedules')
  products.value = Object.fromEntries((await api.get('products')).map((p) => [p.key, p]))
})
</script>

<template>
  <main class="page stack-lg">
    <router-link to="/mehr" class="small muted">Zurück</router-link>
    <h1>Düngeschema</h1>
    <p class="muted">Herstellerangaben in ml pro Liter (Microbes in g). Der Gieß-Assistent startet immer hier und reduziert nur – er geht nie darüber.</p>
    <section v-for="s in schedules" :key="s.id" class="stack">
      <h2>{{ s.name }}</h2>
      <p class="small muted">Stand {{ s.version }}, abgerufen {{ fmt.date(s.retrieved_on) }}. <a :href="s.source_url" target="_blank" rel="noopener">Quelle</a></p>
      <div style="overflow-x:auto">
        <table class="num">
          <thead><tr><th>Produkt</th><th v-for="h in HEAD" :key="h" class="r">{{ h }}</th></tr></thead>
          <tbody>
            <tr v-for="(row, key) in s.table" :key="key" :class="{ off: products[key] && !products[key].in_stock }">
              <td>{{ products[key]?.name || key }}</td>
              <td v-for="st in STAGES" :key="st" class="r">{{ row[st] ? fmt.n(row[st]) : '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <p class="small muted">Grau: nicht im Inventar. BioBizz veröffentlicht kein eigenes Auto-Schema; die App staucht die Blüte-Spalten auf die Blütedauer der Sorte.</p>
  </main>
</template>

<style scoped>
tr.off td { color: var(--muted); opacity: .6; }
td, th { white-space: nowrap; }
</style>
