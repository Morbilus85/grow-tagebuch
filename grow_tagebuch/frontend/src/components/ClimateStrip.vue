<script setup>
import { fmt, rating } from '../util.js'
defineProps({ climate: Object, light: Object })
const cls = (r) => rating[r] || ''
</script>

<template>
  <div class="strip">
    <router-link to="/klima" class="cell">
      <span class="small muted">Temperatur</span>
      <span class="num big">{{ fmt.n(climate?.temp) }}<small>°C</small></span>
      <span class="chip" :class="cls(climate?.temp_rating)" v-if="climate?.temp_target">{{ climate.temp_target[0] }}–{{ climate.temp_target[1] }}</span>
    </router-link>
    <router-link to="/klima" class="cell">
      <span class="small muted">Luftfeuchte</span>
      <span class="num big">{{ fmt.n(climate?.rh, 0) }}<small>%</small></span>
    </router-link>
    <router-link to="/klima" class="cell">
      <span class="small muted">VPD Blatt</span>
      <span class="num big">{{ fmt.n(climate?.vpd_leaf ?? climate?.vpd, 2) }}<small>kPa</small></span>
      <span class="chip" :class="cls(climate?.vpd_rating)" v-if="climate?.vpd_target">{{ fmt.n(climate.vpd_target[0]) }}–{{ fmt.n(climate.vpd_target[1]) }}</span>
    </router-link>
    <router-link to="/licht" class="cell">
      <span class="small muted">Licht</span>
      <span class="num big led" :class="{ off: light?.lamp_on === false }">{{ light?.lamp_on === false ? 'aus' : fmt.n(light?.ppfd, 0) }}<small v-if="light?.lamp_on !== false">µmol</small></span>
      <span class="small muted" v-if="light?.level">berechnet: Stufe {{ light.level }}, {{ light.distance_cm }} cm</span>
      <span class="chip" :class="cls(light?.status)" v-if="light?.dli && light?.lamp_on !== false">DLI {{ fmt.n(light.dli) }}</span>
    </router-link>
  </div>
  <p v-if="climate && !climate.available" class="small muted" style="margin-top:8px">
    Keine Sensordaten aus Home Assistant – läuft die App als Add-on?
  </p>
</template>

<style scoped>
.strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--line);
  border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
.cell { background: var(--surface); padding: 10px 10px 12px; display: flex; flex-direction: column; gap: 2px; text-decoration: none; min-width: 0; }
.big { font-size: 1.6rem; font-weight: 600; line-height: 1.1; }
.big small { font-size: .8rem; font-weight: 500; color: var(--muted); margin-left: 2px; }
.led { color: var(--led); }
.led.off { color: var(--muted); }
.chip { align-self: flex-start; font-size: .75rem; padding: 0 8px; }
@media (max-width: 420px) { .strip { grid-template-columns: repeat(2, 1fr); } }
</style>
