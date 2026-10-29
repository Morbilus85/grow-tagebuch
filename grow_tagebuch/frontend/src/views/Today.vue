<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { api, photoUrl } from '../api.js'
import { fmt, LOG_TYPES, PEST, rating, say } from '../util.js'
import PhaseBar from '../components/PhaseBar.vue'
import ClimateStrip from '../components/ClimateStrip.vue'

const data = ref(null)
const err = ref('')
let timer

async function load() {
  try { data.value = await api.get('today'); err.value = '' } catch (e) { err.value = e.message }
}
async function done(t) {
  await api.post(`tasks/${t.id}/done`)
  say(`„${t.title}“ erledigt`)
  load()
}
onMounted(() => { load(); timer = setInterval(load, 60000) })
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <main class="page stack-lg">
    <p v-if="err" class="note bad">Daten konnten nicht geladen werden: {{ err }}</p>
    <template v-if="data">
      <div v-if="!data.runs.length" class="panel empty stack">
        <h2>Kein aktiver Durchgang</h2>
        <p class="muted">Lege unter „Mehr“ einen Run an.</p>
      </div>

      <section v-for="r in data.runs" :key="r.run.id" class="stack">
        <div class="row between">
          <div>
            <h1>{{ r.run.name }}</h1>
            <p class="small muted">{{ fmt.dateLong(data.date) }}, Licht {{ r.run.light_hours }}/{{ 24 - r.run.light_hours }}</p>
          </div>
          <router-link :to="`/run/${r.run.id}`" class="btn ghost small">Bearbeiten</router-link>
        </div>
        <p v-if="data.legal && data.legal.status !== 'ok'" class="note" :class="data.legal.status === 'ueber' ? 'bad' : 'warn'">
          {{ data.legal.living_plants }} von {{ data.legal.plant_limit }} erlaubten Pflanzen
          ({{ data.legal.adults }} Erwachsene × 3 nach KCanG){{ data.legal.status === 'ueber' ? ' – Grenze überschritten.' : '.' }}
        </p>

        <router-link v-for="c in r.cases" :key="c.id" :to="`/schaedlinge/${c.id}`" class="note case" :class="PEST.statusClass[c.status]">
          <strong>{{ c.name }}</strong> – {{ PEST.scope(c, r.plants.map((s) => s.plant)) }}, {{ PEST.status[c.status] }}
          <span v-if="c.next_task" class="small muted"><br />Nächster Schritt {{ fmt.date(c.next_task.due_on) }}: {{ c.next_task.title }}</span>
        </router-link>

        <ClimateStrip :climate="r.climate" :light="r.light" />
        <p v-for="m in r.light.messages" :key="m" class="note warn small">{{ m }}</p>

        <div v-if="r.tasks.length" class="panel stack">
          <h3>Fällig</h3>
          <div v-for="t in r.tasks" :key="t.id" class="row between">
            <span>{{ t.title }}</span>
            <button class="ghost" @click="done(t)">Erledigt</button>
          </div>
        </div>

        <div v-if="!r.plants.length" class="panel empty stack">
          <h2>Noch keine Pflanzen</h2>
          <p class="muted">Trage deine Samen ein – mit Datum Einweichen, Gesetzt und Aufgelaufen.</p>
          <router-link :to="`/run/${r.run.id}`" class="btn primary">Pflanze anlegen</router-link>
        </div>

        <article v-for="s in r.plants" :key="s.plant.id" class="panel plant">
          <router-link :to="`/pflanze/${s.plant.id}`" class="head">
            <div class="day num" v-if="s.phase.day">
              <small>Tag</small>{{ s.phase.day }}
            </div>
            <div class="grow">
              <h2>{{ s.plant.name }}</h2>
              <p class="small muted">{{ s.strain?.name }}</p>
              <span class="chip ok">{{ s.phase.label }}</span>
            </div>
            <img v-if="s.last_photo_id" :src="photoUrl(s.last_photo_id, true)" alt="" class="thumb" />
          </router-link>

          <PhaseBar v-if="s.phase.day" :phase="s.phase" :sprouted="s.plant.sprouted_on" />

          <ul class="todo">
            <li v-for="a in s.actions" :key="a">{{ a }}</li>
            <li v-for="m in s.space.messages" :key="m" :class="rating[s.space.status]">{{ m }}</li>
          </ul>

          <p v-if="s.germination?.next_hint" class="small muted">In etwa {{ fmt.n(s.germination.next_in_hours, 0) }} h: {{ s.germination.next_hint }}</p>
          <router-link v-if="s.germination && !s.germination.method_key" class="btn small" :to="{ path: '/keimung', query: { plant: s.plant.id } }">Keimmethode wählen</router-link>

          <div v-if="s.training_now?.length || s.training_wait" class="training">
            <span class="small muted">Training jetzt möglich:</span>
            <router-link v-for="t in s.training_now" :key="t.key" :to="{ path: `/training/${t.key}`, query: { plant: s.plant.id } }"
                         class="chip" :class="t.priority ? 'ok' : ''">{{ t.name }}</router-link>
            <p v-if="s.training_wait" class="small" style="color:var(--amber)">{{ s.training_wait.reason }}</p>
          </div>

          <router-link v-if="s.last_log" :to="`/pflanze/${s.plant.id}`" class="small muted lastlog">
            Letzter Eintrag: {{ LOG_TYPES[s.last_log.type] || 'Notiz' }}, {{ fmt.dt(s.last_log.ts) }}<template v-if="s.last_log.text"> – {{ s.last_log.text }}</template>
          </router-link>
          <p class="small muted" v-if="s.last_watering">
            Zuletzt gegossen {{ s.last_watering.days_ago === 0 ? 'heute' : s.last_watering.days_ago === 1 ? 'gestern' : `vor ${s.last_watering.days_ago} Tagen` }}
            ({{ fmt.vol(s.last_watering.volume_l) }})
          </p>

          <div class="row actions">
            <router-link class="btn primary" :to="{ path: '/giessen', query: { run: r.run.id, plant: s.plant.id } }">Gießen</router-link>
            <router-link class="btn" :to="{ path: '/eintrag', query: { plant: s.plant.id, type: 'observation', photo: 1 } }">Foto</router-link>
            <router-link class="btn" :to="{ path: '/eintrag', query: { plant: s.plant.id, type: 'measurement' } }">Höhe</router-link>
            <router-link class="btn" :to="{ path: '/eintrag', query: { plant: s.plant.id } }">Eintrag</router-link>
          </div>
        </article>
      </section>
    </template>
  </main>
</template>

<style scoped>
.plant .head { display: flex; gap: 14px; align-items: flex-start; text-decoration: none; }
.day { font-size: 3.2rem; font-weight: 600; line-height: .9; min-width: 64px; color: var(--leaf); }
.day small { display: block; font-size: .8rem; font-weight: 500; color: var(--muted); line-height: 1.4; }
.thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 10px; }
.training { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 4px 0 8px; }
.training .chip { text-decoration: none; }
.case { display: block; text-decoration: none; }
.lastlog { display: block; margin: 4px 0; }
.todo { margin: 12px 0 8px; padding-left: 18px; }
.todo li { margin: 4px 0; }
.todo li.warn { color: var(--amber); }
.todo li.bad { color: var(--alarm); font-weight: 600; }
.actions { margin-top: 12px; }
.actions .btn { flex: 1; min-width: 0; padding: 10px 8px; }
</style>
