<script setup>
import { computed } from 'vue'
import { fmt } from '../util.js'

const props = defineProps({ phase: Object, sprouted: String })
const DAY = 86400000

const segs = computed(() => {
  const p = props.phase
  if (!p || !p.harvest_date || !props.sprouted) return null
  const s = new Date(props.sprouted)
  const total = Math.round((new Date(p.harvest_date) - s) / DAY) + 1
  const pf = Math.round((new Date(p.preflower_date) - s) / DAY) + 1
  const seedEnd = Math.min(14, pf - 1)
  const flushStart = total - 7
  const parts = [
    { key: 'seedling', label: 'Sämling', days: seedEnd },
    { key: 'veg', label: 'Wachstum', days: pf - 1 - seedEnd },
    { key: 'bloom', label: 'Blüte', days: flushStart - pf + 1 },
    { key: 'flush', label: 'Reife', days: 7 },
  ].filter((x) => x.days > 0)
  return { total, parts, pos: Math.min(Math.max(((p.day - 0.5) / total) * 100, 0), 100) }
})
</script>

<template>
  <div v-if="segs" class="pbar" :aria-label="`Tag ${phase.day} von ca. ${segs.total}`">
    <div class="track">
      <div v-for="s in segs.parts" :key="s.key" class="seg" :class="[s.key, { now: phase.phase === s.key }]"
           :style="{ flexGrow: s.days }"><span>{{ s.label }}</span></div>
      <div class="marker" :style="{ left: segs.pos + '%' }"></div>
    </div>
    <div class="row between small muted">
      <span>Vorblüte {{ phase.preflower_estimated ? 'ca. ' : '' }}{{ fmt.date(phase.preflower_date) }}</span>
      <span>Ernte ca. {{ fmt.date(phase.harvest_date) }}</span>
    </div>
  </div>
</template>

<style scoped>
.pbar { margin-top: 12px; }
.track { position: relative; display: flex; gap: 2px; height: 26px; margin-bottom: 6px; }
.seg span { overflow: hidden; text-overflow: ellipsis; }
.seg { flex-basis: 0; min-width: 0; border-radius: 6px; background: var(--sunken); color: var(--muted); font-size: .75rem;
  display: flex; align-items: center; padding: 0 6px; overflow: hidden; white-space: nowrap; }
.seg.now { background: var(--ok-bg); color: var(--leaf); font-weight: 600; }
.marker { position: absolute; top: -4px; bottom: -4px; width: 3px; margin-left: -1.5px; border-radius: 2px; background: var(--ink); }
</style>
