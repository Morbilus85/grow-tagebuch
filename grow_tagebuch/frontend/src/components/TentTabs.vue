<script setup>
import { onMounted } from 'vue'
import { loadTents, setTent, tent } from '../tent.js'

const emit = defineEmits(['change'])
const MEDIUM = { erde: 'Erde', rdwc: 'RDWC' }
function pick(id) {
  if (id === tent.id) return
  setTent(id)
  emit('change', id)
}
onMounted(() => { if (!tent.loaded) loadTents() })
</script>

<template>
  <nav v-if="tent.list.length > 1" class="tenttabs" role="tablist" aria-label="Zelt">
    <button v-for="s in tent.list" :key="s.id" role="tab" :aria-selected="s.id === tent.id"
            :class="{ on: s.id === tent.id }" @click="pick(s.id)">
      <span class="name">{{ s.name }}</span>
      <span class="sub">{{ MEDIUM[s.medium] || s.medium }}{{ s.run ? '' : ' · leer' }}</span>
    </button>
  </nav>
</template>

<style scoped>
.tenttabs { display: flex; gap: 4px; border-bottom: 2px solid var(--leaf); margin-bottom: -8px; overflow-x: auto; }
.tenttabs button {
  flex: 1 1 0; min-width: 120px; display: flex; flex-direction: column; align-items: flex-start; gap: 0;
  padding: 8px 14px 7px; border: 1px solid var(--line); border-bottom: 0; border-radius: 12px 12px 0 0;
  background: var(--sunken); color: var(--muted); text-align: left; min-height: 0;
}
.tenttabs button.on { background: var(--leaf); color: var(--leaf-ink); border-color: var(--leaf); }
.name { font-weight: 600; font-size: 1rem; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.sub { font-size: .78rem; opacity: .85; }
</style>
