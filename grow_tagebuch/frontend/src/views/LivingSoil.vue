<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { fmt, say, today } from '../util.js'

const route = useRoute()
const router = useRouter()
const info = ref(null)
const batches = ref([])
const tab = ref(route.query.tab || 'rezepte')
const recipeKey = computed(() => route.params.key)
const recipe = computed(() => info.value?.recipes.find((r) => r.key === recipeKey.value))
const volume = ref(66)
const choices = ref({})
const withOptional = ref(true)
const calc = ref(null)
const batchName = ref('')
const startDate = ref(today())

const TYPE = { diy: 'Selbst gemischt', allinone: 'All-in-One', reamend: 'Aufbereitung' }
const STATUS = { reift: 'reift', fertig: 'fertig', verwendet: 'verwendet' }

const recipes = computed(() => info.value?.recipes || [])
const ingByRole = computed(() => {
  const g = {}
  for (const i of info.value?.ingredients || []) {
    ;(g[i.role] ||= []).push(i)
  }
  return g
})
const owned = computed(() => new Set(info.value?.owned || []))

async function load() {
  info.value = await api.get('living-soil')
  batches.value = await api.get('living-soil/batches')
  if (recipe.value) {
    if (recipe.value.type === 'reamend') volume.value = 60
    await recalc()
  }
}
async function recalc() {
  calc.value = await api.post('living-soil/calc', { recipe_key: recipeKey.value, volume_l: volume.value, choices: choices.value, include_optional: withOptional.value })
  choices.value = Object.fromEntries(calc.value.bulk.map((b) => [b.role, b.key]))
}
async function setMode(mode) {
  await api.put('living-soil/mode', { mode })
  say(mode === 'vegan' ? 'Anbauweise: vegan' : 'Anbauweise: vegan und tierisch')
  await load()
}
async function toggleOwned(key) {
  const s = new Set(info.value.owned)
  s.has(key) ? s.delete(key) : s.add(key)
  info.value.owned = (await api.put('living-soil/owned', { keys: [...s] })).owned
}
async function startBatch() {
  await api.post('living-soil/batches', { recipe_key: recipeKey.value, volume_l: volume.value, choices: choices.value,
    include_optional: withOptional.value, name: batchName.value || undefined, started_on: startDate.value })
  say('Ansatz angelegt – Aufgaben zum Befeuchten und Wenden erscheinen auf „Heute“')
  router.push({ path: '/living-soil', query: { tab: 'ansaetze' } })
}
async function setStatus(b, status) {
  await api.patch(`living-soil/batches/${b.id}`, { status })
  load()
}
async function toSoil(b) {
  const s = await api.post(`living-soil/batches/${b.id}/soil`)
  say(`Erdprofil „${s.name}“ angelegt – im Durchgang unter „Erde“ auswählen`)
  load()
}
async function delBatch(b) {
  if (!confirm(`Ansatz „${b.name}“ löschen?`)) return
  await api.del(`living-soil/batches/${b.id}`)
  load()
}
const amt = (x) => (x.amount === null || x.amount === undefined ? 'laut Etikett' : `${fmt.n(x.amount, x.unit === 'l' ? 1 : 1)} ${x.unit}`)
watch(() => route.params.key, () => { calc.value = null; choices.value = {}; load() })
watch(() => route.query.tab, (t) => { if (t) tab.value = t })
onMounted(load)
</script>

<template>
  <main class="page stack-lg" v-if="info">
    <template v-if="!info.mode">
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1>Living Soil</h1>
      <p class="lead">Wie möchtest du anbauen?</p>
      <p class="muted">Davon hängt ab, welche Zutaten, Rezepte und Top-Dress-Vorschläge die App anzeigt. Du kannst das später jederzeit ändern.</p>
      <button class="panel choice" @click="setMode('vegan')">
        <h3>Vegan</h3>
        <p class="small muted">Nur pflanzliche und mineralische Zutaten: Neem, Kelp, Rohphosphat, Gesteinsmehle, Wurmhumus.</p>
      </button>
      <button class="panel choice" @click="setMode('alle')">
        <h3>Vegan und tierisch</h3>
        <p class="small muted">Zusätzlich Knochenmehl, Krabbenschalenmehl, Fledermausguano, Hornspäne, Fischmehl, Hühnermist. Vegane Rezepte bleiben sichtbar.</p>
      </button>
    </template>

    <template v-else-if="!recipe">
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1>Living Soil</h1>
      <div class="row" role="tablist">
        <button v-for="[k, l] in [['rezepte', 'Rezepte'], ['ansaetze', 'Ansätze'], ['zutaten', 'Zutaten'], ['tees', 'Tees & Top-Dress']]" :key="k"
                role="tab" :aria-selected="tab === k" :class="{ primary: tab === k }" @click="tab = k">{{ l }}</button>
      </div>
      <p class="row small muted">Anbauweise: {{ info.mode === 'vegan' ? 'vegan' : 'vegan und tierisch' }}
        <button class="ghost mini" @click="setMode(info.mode === 'vegan' ? 'alle' : 'vegan')">ändern</button></p>

      <section v-if="tab === 'rezepte'" class="stack">
        <p class="muted">Mengen sind Richtwerte aus bewährten Community-Rezepten und Herstellerangaben – keine exakte Wissenschaft.</p>
        <router-link v-for="r in recipes" :key="r.key" :to="`/living-soil/rezept/${r.key}`" class="panel card">
          <div class="row between"><h3>{{ r.name }}</h3>
            <span class="row"><span class="chip">{{ TYPE[r.type] }}</span><span class="chip" :class="r.vegan ? 'ok' : 'warn'">{{ r.vegan ? 'vegan' : 'tierisch' }}</span></span></div>
          <p class="small">{{ r.summary }}</p>
          <p class="small muted">Reifezeit {{ r.rest_days[1] ? `${r.rest_days[0]}–${r.rest_days[1]} Tage` : 'keine' }}</p>
        </router-link>
      </section>

      <section v-if="tab === 'ansaetze'" class="stack">
        <p v-if="!batches.length" class="muted">Noch kein Ansatz. Wähle ein Rezept und starte von dort.</p>
        <article v-for="b in batches" :key="b.id" class="panel stack">
          <div class="row between">
            <h3>{{ b.name }}</h3>
            <span class="chip" :class="{ ok: b.status === 'fertig', warn: b.status === 'reift' }">{{ STATUS[b.status] }}</span>
          </div>
          <p class="small muted">{{ fmt.n(b.volume_l, 0) }} l, angesetzt {{ fmt.date(b.started_on) }}<template v-if="b.ready_on">, fertig ab ca. {{ fmt.date(b.ready_on) }}</template></p>
          <details>
            <summary class="small">Zutaten</summary>
            <ul class="small">
              <li v-for="x in [...b.calc.bulk, ...b.calc.amendments]" :key="x.key">{{ x.name }}: {{ amt(x) }}</li>
            </ul>
          </details>
          <div class="row">
            <button v-if="b.status === 'reift'" @click="setStatus(b, 'fertig')">Als fertig markieren</button>
            <button v-if="!b.soil_id" class="primary" @click="toSoil(b)">Als Erde für einen Durchgang nutzen</button>
            <span v-else class="small muted">Als Erdprofil angelegt</span>
            <button v-if="b.status !== 'verwendet'" class="ghost" @click="setStatus(b, 'verwendet')">Verbraucht</button>
            <button class="ghost" @click="delBatch(b)">Löschen</button>
          </div>
        </article>
      </section>

      <section v-if="tab === 'zutaten'" class="stack">
        <p class="muted">Hake an, was du im Haus hast. Die Rezepte zeigen dann, was noch fehlt.</p>
        <div v-for="(items, role) in ingByRole" :key="role" class="stack">
          <h3>{{ info.roles[role] }}</h3>
          <label v-for="i in items" :key="i.key" class="ing">
            <input type="checkbox" :checked="owned.has(i.key)" @change="toggleOwned(i.key)" />
            <span><strong>{{ i.name }}</strong><span v-if="i.npk" class="small muted"> NPK {{ i.npk }}</span>
              <span v-if="!i.vegan" class="chip warn" style="margin-left:6px">tierisch</span><br />
              <span class="small muted">{{ i.note }}</span></span>
          </label>
        </div>
      </section>

      <section v-if="tab === 'tees'" class="stack">
        <p class="muted">Im Living Soil wird nicht aus der Flasche gedüngt. Tees und Top-Dress halten das Bodenleben aktiv. Der Gieß-Assistent schlägt sie passend zur Phase vor.</p>
        <article v-for="t in info.teas" :key="t.key" class="panel stack">
          <div class="row between"><h3>{{ t.name }}</h3><span class="small muted">alle {{ t.interval_days }} Tage</span></div>
          <p class="small">{{ t.summary }}</p>
          <ol class="steps small"><li v-for="s in t.steps" :key="s">{{ s }}</li></ol>
        </article>
      </section>
    </template>

    <template v-else>
      <router-link to="/living-soil" class="small muted">Alle Rezepte</router-link>
      <div>
        <h1>{{ recipe.name }}</h1>
        <div class="row" style="margin-top:6px">
          <span class="chip">{{ TYPE[recipe.type] }}</span>
          <span class="chip" :class="recipe.vegan ? 'ok' : 'warn'">{{ recipe.vegan ? 'vegan' : 'tierisch' }}</span>
        </div>
      </div>
      <p class="lead">{{ recipe.summary }}</p>

      <section class="panel stack">
        <div class="grid2">
          <label class="field"><span>{{ recipe.type === 'reamend' ? 'Gebrauchte Erde (l)' : 'Menge fertige Mischung (l)' }}</span>
            <input type="number" min="5" step="5" v-model.number="volume" @change="recalc" /></label>
          <label class="row" style="align-self:end"><input type="checkbox" v-model="withOptional" @change="recalc" /> Optionale Zutaten</label>
        </div>
        <p class="small muted" v-if="calc">{{ calc.volume_note }} 3 Töpfe à 20 l = 60 l, mit Reserve 66 l.</p>
      </section>

      <template v-if="calc">
        <section class="stack">
          <h2>Grundmischung</h2>
          <div v-for="b in calc.bulk" :key="b.role" class="row line">
            <div class="grow">
              <p class="small muted">{{ b.role_label }} ({{ Math.round(b.share * 100) }} %)</p>
              <select v-model="choices[b.role]" @change="recalc"><option v-for="o in b.options" :key="o.key" :value="o.key">{{ o.name }}</option></select>
            </div>
            <div class="amount num" :class="{ miss: !b.owned }">{{ fmt.n(b.amount) }} l</div>
          </div>
        </section>

        <section class="stack">
          <h2>{{ recipe.type === 'allinone' ? 'Dünger' : 'Amendments' }}</h2>
          <table>
            <tbody>
              <tr v-for="a in calc.amendments" :key="a.key">
                <td>{{ a.name }}<span v-if="a.optional" class="small muted"> (optional)</span><br />
                  <span class="small muted">{{ a.role_label }}<template v-if="a.per_l">, {{ fmt.n(a.per_l) }} {{ a.unit }}/l</template><template v-if="a.note">, {{ a.note }}</template></span></td>
                <td class="r num amount" :class="{ miss: !a.owned }">{{ amt(a) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="small muted">Grau markiert: hast du laut Zutatenliste noch nicht.</p>
        </section>

        <section v-if="calc.shopping.length" class="panel stack">
          <h3>Einkaufsliste</h3>
          <ul><li v-for="s in calc.shopping" :key="s.name">{{ s.name }}: {{ s.amount !== null ? `${fmt.n(s.amount)} ${s.unit}` : 'laut Etikett' }}</li></ul>
        </section>

        <section class="stack">
          <h2>So geht's</h2>
          <ol class="steps"><li v-for="s in recipe.steps" :key="s">{{ s }}</li></ol>
          <p v-for="w in recipe.warnings" :key="w" class="note warn">{{ w }}</p>
        </section>

        <section class="panel stack">
          <h3>Ansatz starten</h3>
          <div class="grid2">
            <label class="field"><span>Name</span><input v-model="batchName" :placeholder="recipe.name" /></label>
            <label class="field"><span>Angesetzt am</span><input type="date" v-model="startDate" /></label>
          </div>
          <p class="small muted" v-if="recipe.rest_days[1]">Die App legt Aufgaben an: Feuchte alle 3 Tage prüfen, wöchentlich wenden, Erinnerung nach {{ recipe.rest_days[0] }} Tagen.</p>
          <button class="primary" @click="startBatch">Ansatz anlegen</button>
        </section>
      </template>
    </template>
  </main>
</template>

<style scoped>
.card { display: block; text-decoration: none; }
.choice { display: block; width: 100%; text-align: left; cursor: pointer; }
.choice > * + * { margin-top: 6px; }
.mini { min-height: 32px; padding: 2px 10px; font-size: .875rem; }
.card > * + * { margin-top: 6px; }
.lead { font-size: 1.1rem; }
.line { align-items: flex-end; flex-wrap: nowrap; }
.amount { font-weight: 600; font-size: 1.15rem; white-space: nowrap; min-width: 84px; text-align: right; }
.amount.miss { color: var(--muted); }
.ing { display: flex; gap: 10px; align-items: flex-start; padding: 6px 0; }
.ing input { margin-top: 3px; flex: none; }
.steps { padding-left: 22px; }
.steps li { margin: 6px 0; }
ul { padding-left: 20px; }
</style>
