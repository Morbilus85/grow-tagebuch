<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'
import { fmt, say, today } from '../util.js'

const tasks = ref([])
const runs = ref([])
const newTask = ref({ title: '', interval_days: 7, due_on: today() })
async function load() { [tasks.value, runs.value] = await Promise.all([api.get('tasks'), api.get('runs')]) }
async function addTask() {
  await api.post('tasks', { ...newTask.value, run_id: runs.value.find((r) => r.status === 'aktiv')?.id })
  newTask.value = { title: '', interval_days: 7, due_on: today() }
  say('Aufgabe angelegt')
  load()
}
async function delTask(t) { if (confirm(`„${t.title}“ löschen?`)) { await api.del(`tasks/${t.id}`); load() } }
onMounted(load)
</script>

<template>
  <main class="page stack-lg">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1 style="margin-top:8px">Aufgaben</h1>
      <p class="small muted">Fällige Aufgaben erscheinen unter „Heute“ und werden dort abgehakt.</p>
    </div>
    <section class="stack">
      <div v-for="t in tasks" :key="t.id" class="row between panel flat" style="padding:10px 12px">
        <span>{{ t.title }} <span class="small" :class="t.due_on <= today() ? '' : 'muted'">{{ t.interval_days ? `alle ${t.interval_days} Tage` : 'einmalig' }}, fällig {{ fmt.date(t.due_on) }}</span></span>
        <button class="ghost" @click="delTask(t)">Löschen</button>
      </div>
      <p v-if="!tasks.length" class="muted">Keine Aufgaben.</p>
    </section>
    <form class="panel stack" @submit.prevent="addTask">
      <h3>Neue Aufgabe</h3>
      <input v-model="newTask.title" placeholder="z. B. Töpfe drehen" required />
      <div class="grid2">
        <label class="field"><span>Alle … Tage (0 = einmalig)</span><input type="number" v-model.number="newTask.interval_days" min="0" /></label>
        <label class="field"><span>Fällig am</span><input type="date" v-model="newTask.due_on" /></label>
      </div>
      <button>Anlegen</button>
    </form>
  </main>
</template>
