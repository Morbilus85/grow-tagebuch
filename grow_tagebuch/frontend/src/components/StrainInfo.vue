<script setup>
import { computed } from 'vue'

// Steckbrief einer Sorte. compact = Kurzfassung (Pflanzenseite, Samen eintragen)
const props = defineProps({ strain: Object, compact: Boolean })
const i = computed(() => props.strain?.info || {})
const RCLASS = { top: 'ok', gut: '', vorsicht: 'warn', nein: 'bad' }
const duration = computed(() => {
  const s = props.strain
  if (!s) return null
  const breeder = i.value.seed_to_harvest_text || (s.auto ? (s.seed_to_harvest_days && `${s.seed_to_harvest_days} Tage`) : (s.flowering_days && `${s.flowering_days} Tage Blüte`))
  return breeder
})
const facts = computed(() => {
  const s = props.strain || {}
  return [
    ['Typ', [s.auto ? 'Autoflower' : 'Photoperiodisch', i.value.type].filter(Boolean).join(', ')],
    ['Genetik', s.genetics],
    ['THC / CBD', [i.value.thc, i.value.cbd].filter(Boolean).join(' / ')],
    [s.auto ? 'Samen bis Ernte' : 'Blüte', duration.value],
    ['Laut Growern', i.value.grower_days],
    ['Höhe', i.value.height_text || (s.max_height_cm && `bis ${s.max_height_cm} cm`)],
    ['Ertrag', [i.value.yield_indoor && `Indoor ${i.value.yield_indoor}`, i.value.yield_outdoor && `Outdoor ${i.value.yield_outdoor}`].filter(Boolean).join(', ')],
    ['Schwierigkeit', i.value.difficulty],
    ['Wuchs', i.value.structure],
    ['Aroma', [i.value.aroma, i.value.terpenes && `Terpene: ${i.value.terpenes}`].filter(Boolean).join('. ')],
    ['Wirkung', i.value.effect],
  ].filter(([, v]) => v)
})
const shownFacts = computed(() => props.compact ? facts.value.filter(([k]) => ['Typ', 'Samen bis Ernte', 'Blüte', 'Laut Growern', 'Höhe', 'Schwierigkeit'].includes(k)) : facts.value)
const training = computed(() => (props.strain?.training || []).filter((t) => !props.compact || t.rating === 'top' || t.rating === 'gut'))
</script>

<template>
  <div v-if="strain" class="strain stack">
    <dl class="facts">
      <template v-for="[k, v] in shownFacts" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template>
    </dl>

    <div v-if="!compact && i.specials?.length">
      <h4>Besonderheiten</h4>
      <ul><li v-for="x in i.specials" :key="x">{{ x }}</li></ul>
    </div>
    <div v-if="!compact && i.grow_tips?.length">
      <h4>Anbautipps</h4>
      <ul><li v-for="x in i.grow_tips" :key="x">{{ x }}</li></ul>
    </div>

    <div v-if="training.length">
      <h4>{{ compact ? 'Passendes Training' : 'Training für diese Sorte' }}</h4>
      <div v-if="compact" class="row chips">
        <router-link v-for="t in training" :key="t.key" :to="`/training/${t.key}`" class="chip" :class="RCLASS[t.rating]">{{ t.name }}</router-link>
      </div>
      <div v-else class="trows">
        <router-link v-for="t in training" :key="t.key" :to="`/training/${t.key}`" class="trow">
          <span><strong>{{ t.name }}</strong><br /><span class="small muted">{{ t.reason }}</span></span>
          <span class="chip" :class="RCLASS[t.rating]">{{ t.label }}</span>
        </router-link>
      </div>
    </div>

    <p v-if="!compact && i.sources?.length" class="small muted">
      Quellen: <template v-for="(q, n) in i.sources" :key="q.url"><a :href="q.url" target="_blank" rel="noopener">{{ q.title }}</a><template v-if="n < i.sources.length - 1">, </template></template>
    </p>
    <p v-if="!compact && i.updated_at" class="small muted">Stand {{ new Date(i.updated_at).toLocaleDateString('de-DE') }}<template v-if="i.source === 'internet'">, aus dem Internet recherchiert</template>.
      Breeder-Angaben gelten für Idealbedingungen.</p>
  </div>
</template>

<style scoped>
.facts { display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0; }
.facts dt { color: var(--muted); font-size: .875rem; padding-top: 1px; }
.facts dd { margin: 0; }
h4 { font: 600 .95rem var(--cond); margin: 0 0 4px; }
ul { margin: 0; padding-left: 18px; }
li { margin: 2px 0; }
.chips { gap: 6px; }
.trows { display: flex; flex-direction: column; }
.trow { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--line); text-decoration: none; }
.trow:last-child { border-bottom: 0; }
.trow .chip { flex: none; }
</style>
