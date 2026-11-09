<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { today } from '../util.js'

const d = ref({ runs: [], strains: [], tasks: [], soils: [], waters: [], notify: null })

async function load() {
  const [runs, strains, tasks, soils, waters, notify] = await Promise.all(
    ['runs', 'strains', 'tasks', 'soils', 'waters', 'notify'].map((p) => api.get(p).catch(() => null)))
  d.value = { runs: runs || [], strains: strains || [], tasks: tasks || [], soils: soils || [], waters: waters || [], notify }
}
onMounted(load)

const activeRun = computed(() => d.value.runs.find((r) => r.status === 'aktiv'))
const dueTasks = computed(() => d.value.tasks.filter((t) => t.due_on && t.due_on <= today()).length)
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`

const groups = computed(() => [
  { title: 'Grow', items: [
    { to: '/mehr/durchgaenge', name: 'Durchgänge', hint: activeRun.value ? `Aktiv: ${activeRun.value.name}` : plural(d.value.runs.length, 'Durchgang', 'Durchgänge') },
    { to: '/mehr/sorten', name: 'Sorten', hint: plural(d.value.strains.length, 'Sorte', 'Sorten') + ' mit Steckbrief' },
    { to: '/mehr/aufgaben', name: 'Aufgaben', hint: dueTasks.value ? `${dueTasks.value} fällig` : plural(d.value.tasks.length, 'Aufgabe', 'Aufgaben') },
  ] },
  { title: 'Erde, Wasser & Dünger', items: [
    { to: '/mehr/erde-wasser', name: 'Erde & Wasser', hint: [d.value.soils[0]?.product || d.value.soils[0]?.name, d.value.waters[0]?.name].filter(Boolean).join(' · ') || 'Erde, Wasserwerte' },
    { to: '/inventar', name: 'Inventar', hint: 'Dünger, Zusätze, Dosierungen' },
    { to: '/schema', name: 'Düngeschema', hint: 'BioBizz All-Mix und Light-Mix' },
    { to: '/living-soil', name: 'Living Soil', hint: 'Rezepte, Ansätze, Zutaten, Tees' },
  ] },
  { title: 'Wissen', items: [
    { to: '/keimung', name: 'Keimung', hint: 'Methoden, Mischverhältnisse, Zeitplan' },
    { to: '/training', name: 'Training', hint: 'Techniken mit Anleitung' },
    { to: '/schaedlinge', name: 'Schädlinge & Krankheiten', hint: 'Befälle, Maßnahmen, Verlauf' },
  ] },
  { title: 'App', items: [
    { to: '/mehr/einstellungen', name: 'Einstellungen', hint: `Push ${d.value.notify?.enabled ? 'aktiv' : 'aus'} · Sensoren · Haushalt · Export` },
  ] },
])
</script>

<template>
  <main class="page stack-lg">
    <h1>Mehr</h1>
    <section v-for="g in groups" :key="g.title" class="stack">
      <h2 class="small muted group">{{ g.title }}</h2>
      <div class="grid2">
        <router-link v-for="i in g.items" :key="i.to" :to="i.to" class="panel link tile">
          <h3>{{ i.name }}</h3><p class="small muted">{{ i.hint }}</p>
        </router-link>
      </div>
    </section>
  </main>
</template>

<style scoped>
.link { text-decoration: none; }
.group { text-transform: uppercase; letter-spacing: .06em; margin: 0; font-weight: 600; }
.tile p { margin: 4px 0 0; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
</style>
