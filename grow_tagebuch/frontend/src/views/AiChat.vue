<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, photoUrl } from '../api.js'
import { fmt, say, shrinkImage } from '../util.js'

const route = useRoute()
const router = useRouter()
const chat = ref(null)
const msgs = ref([])
const text = ref('')
const files = ref([]) // {file, url, what}
const sending = ref(false)
const big = ref(null)
const fileInput = ref(null)
const pendingWhat = ref('')
let timer = null

const AMPEL = { unauffaellig: ['Unauffällig', 'ok'], beobachten: ['Beobachten', 'warn'], handeln: ['Handeln', 'bad'] }
const CONF = { hoch: 'bad', mittel: 'warn', niedrig: '' }
const back = computed(() => chat.value?.plant_id ? `/pflanze/${chat.value.plant_id}` : `/klima?zelt=${chat.value?.setup_id || ''}`)
const lastAssistant = computed(() => [...msgs.value].reverse().find((m) => m.role === 'assistant'))

async function load(scroll = false) {
  const d = await api.get(`ai/chats/${route.params.id}`)
  const grew = d.messages.length !== msgs.value.length
  chat.value = d.chat
  msgs.value = d.messages
  clearTimeout(timer)
  if (d.chat.busy) timer = setTimeout(() => load(true), 2500)
  if (scroll && grew) { await nextTick(); window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }) }
}
function askPhoto(what) {
  pendingWhat.value = what || ''
  fileInput.value?.click()
}
// Einzeln wählen (kein `multiple`)
function onFile(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) { say('Kein Foto übernommen – bitte noch einmal wählen'); return }
  files.value.push({ file: f, url: URL.createObjectURL(f), what: pendingWhat.value })
  if (pendingWhat.value && !text.value) text.value = `Hier: ${pendingWhat.value}`
  pendingWhat.value = ''
}
function dropFile(i) { URL.revokeObjectURL(files.value[i].url); files.value.splice(i, 1) }
async function send() {
  if (!text.value.trim() && !files.value.length) return
  sending.value = true
  try {
    const ids = []
    for (const nf of files.value) {
      const fd = new FormData()
      fd.append('file', await shrinkImage(nf.file))
      fd.append('what', nf.what || '')
      const r = await fetch(`api/ai/chats/${chat.value.id}/photos`, { method: 'POST', body: fd })
      if (!r.ok) throw new Error(`Foto nicht hochgeladen (${r.status})`)
      ids.push((await r.json()).id)
    }
    await api.post(`ai/chats/${chat.value.id}/messages`, { text: text.value, photo_ids: ids })
    files.value.forEach((f) => URL.revokeObjectURL(f.url))
    files.value = []
    text.value = ''
    await load(true)
  } catch (e) { say(e.message) } finally { sending.value = false }
}
async function retry() {
  try { await api.post(`ai/chats/${chat.value.id}/retry`); await load() } catch (e) { say(e.message) }
}
async function apply(m, i) {
  try {
    const r = await api.post(`ai/chats/${chat.value.id}/apply`, { message_id: m.id, index: i })
    m.data.suggestions[i] = r
    say(r.task_id ? 'Aufgabe angelegt' : 'Im Tagebuch notiert')
  } catch (e) { say(e.message) }
}
async function remove() {
  if (!confirm('Gespräch löschen? Fotos bleiben im Tagebuch.')) return
  await api.del(`ai/chats/${chat.value.id}`)
  router.replace(back.value)
}
const usd = (v) => `${fmt.n(v, v < 0.1 ? 3 : 2)} $`
onMounted(() => load(true))
onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <main class="page stack-lg" v-if="chat">
    <div>
      <router-link :to="back" class="small muted">Zurück</router-link>
      <div class="row between" style="margin-top:8px">
        <h1>{{ chat.kind === 'check' ? 'KI-Check' : 'KI-Frage' }}</h1>
        <span v-if="AMPEL[chat.ampel]" class="chip" :class="AMPEL[chat.ampel][1]">{{ AMPEL[chat.ampel][0] }}</span>
      </div>
      <p class="muted">{{ chat.title }} · {{ fmt.dt(chat.created_at) }}</p>
    </div>

    <template v-for="m in msgs" :key="m.id">
      <article v-if="m.role === 'user'" class="bubble me stack">
        <div class="thumbs" v-if="m.photo_ids.length">
          <img v-for="p in m.photo_ids" :key="p" :src="photoUrl(p, true)" alt="Foto" @click="big = p" />
        </div>
        <p v-if="m === msgs[0] && chat.previous_photo_id" class="small muted">Zum Vergleich mitgeschickt: Foto vom letzten Check
          <img :src="photoUrl(chat.previous_photo_id, true)" alt="Foto letzter Check" class="prev" @click="big = chat.previous_photo_id" /></p>
        <p v-if="m.text" class="pre">{{ m.text }}</p>
        <p v-else-if="m === msgs[0]" class="small muted">Begutachtung ohne Zusatzfrage</p>
        <p class="small muted">{{ fmt.dt(m.ts) }}</p>
      </article>

      <article v-else class="bubble ai stack">
        <p class="pre">{{ m.data.reply }}</p>

        <div v-if="m.data.comparison" class="note info"><strong>Vergleich zum letzten Check:</strong> {{ m.data.comparison }}</div>

        <div v-if="m.data.findings?.length" class="stack">
          <h3>Befunde</h3>
          <div v-for="(f, i) in m.data.findings" :key="i" class="note" :class="CONF[f.confidence]">
            <div class="row between"><strong>{{ f.title }}</strong><span class="small muted">Sicherheit {{ f.confidence }}</span></div>
            <p class="small">{{ f.evidence }}</p>
            <p v-if="f.against" class="small muted">Dagegen spricht: {{ f.against }}</p>
          </div>
        </div>

        <div v-if="m.data.next_steps?.length">
          <h3>Nächste Schritte</h3>
          <ol class="steps"><li v-for="(s, i) in m.data.next_steps" :key="i">{{ s }}</li></ol>
        </div>

        <div v-if="m.data.photo_requests?.length" class="stack">
          <h3>Bitte noch fotografieren</h3>
          <div v-for="(r, i) in m.data.photo_requests" :key="i" class="row between req">
            <div class="grow"><strong>{{ r.what }}</strong><p class="small muted">{{ r.why }}</p></div>
            <button class="ghost" :disabled="chat.busy || m !== lastAssistant" @click="askPhoto(r.what)">Foto</button>
          </div>
        </div>

        <div v-if="m.data.suggestions?.length" class="stack">
          <h3>Vorschläge</h3>
          <div v-for="(s, i) in m.data.suggestions" :key="i" class="row between req">
            <div class="grow">
              <strong>{{ s.kind === 'aufgabe' ? 'Aufgabe' : 'Notiz' }}: {{ s.title }}</strong>
              <p class="small muted">{{ s.text }}<template v-if="s.kind === 'aufgabe'"> · fällig {{ s.due_in_days ? `in ${s.due_in_days} Tag(en)` : 'heute' }}{{ s.interval_days ? `, alle ${s.interval_days} Tage` : '' }}</template></p>
            </div>
            <span v-if="s.applied" class="chip ok">Übernommen</span>
            <button v-else class="ghost" @click="apply(m, i)">Übernehmen</button>
          </div>
        </div>

        <p class="small muted">{{ fmt.dt(m.ts) }}<template v-if="m.usage?.cost_usd"> · {{ usd(m.usage.cost_usd) }}</template></p>
      </article>
    </template>

    <div v-if="chat.busy" class="bubble ai"><p class="muted">Die KI schaut sich das an … (kann bis zu einer Minute dauern)</p></div>
    <div v-if="chat.error" class="note bad row between">
      <span>{{ chat.error }}</span>
      <button class="ghost" @click="retry">Nochmal</button>
    </div>

    <section class="panel stack" v-if="!chat.busy">
      <div class="thumbs" v-if="files.length">
        <img v-for="(nf, i) in files" :key="i" :src="nf.url" alt="Neues Foto" @click="dropFile(i)" title="Antippen zum Entfernen" />
      </div>
      <label class="field"><span>Rückfrage</span>
        <textarea v-model="text" rows="3" placeholder="z. B. Wie genau mache ich das? Was, wenn ich erst Sonntag gieße?"></textarea>
      </label>
      <div class="row between">
        <label class="btn ghost filebtn">Foto anhängen<input ref="fileInput" type="file" accept="image/*" @change="onFile" /></label>
        <button class="primary" :disabled="sending || (!text.trim() && !files.length)" @click="send">{{ sending ? 'Sendet …' : 'Senden' }}</button>
      </div>
    </section>

    <div class="row between">
      <span class="small muted">Kosten bisher: {{ usd(chat.cost_usd || 0) }}</span>
      <button class="ghost small" @click="remove">Gespräch löschen</button>
    </div>

    <div v-if="big" class="lightbox" @click="big = null" role="dialog" aria-label="Foto">
      <img :src="photoUrl(big)" alt="Foto groß" />
    </div>
  </main>
</template>

<style scoped>
.bubble { border-radius: 12px; padding: 12px 14px; }
.bubble.me { background: var(--sunken); margin-left: 24px; }
.bubble.ai { border: 1px solid var(--line); }
.pre { white-space: pre-wrap; }
.steps { margin: 6px 0 0 1.2em; padding: 0; }
.steps li + li { margin-top: 4px; }
.req { border-left: 3px solid var(--line); padding-left: 12px; }
.prev { width: 48px; height: 48px; object-fit: cover; border-radius: 6px; vertical-align: middle; margin-left: 6px; cursor: zoom-in; }
.filebtn { position: relative; overflow: hidden; cursor: pointer; }
.filebtn input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.thumbs img { cursor: zoom-in; }
.lightbox { position: fixed; inset: 0; z-index: 30; background: rgba(0, 0, 0, .9); display: flex; align-items: center; justify-content: center; }
.lightbox img { max-width: 100%; max-height: 100%; }
</style>
