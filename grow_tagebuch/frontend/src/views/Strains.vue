<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api.js'

const strains = ref([])
onMounted(async () => { strains.value = await api.get('strains') })
</script>

<template>
  <main class="page stack-lg">
    <div>
      <router-link to="/mehr" class="small muted">Zurück</router-link>
      <h1 style="margin-top:8px">Sorten</h1>
    </div>
    <section class="stack">
      <router-link v-for="s in strains" :key="s.id" :to="`/sorte/${s.id}`" class="panel row between link">
        <strong>{{ s.name }}</strong><span class="small muted">{{ s.breeder }}{{ s.info?.thc ? `, THC ${s.info.thc}` : '' }}</span>
      </router-link>
      <p v-if="!strains.length" class="muted">Noch keine Sorten. Sorten legst du beim Durchgang unter „Samen“ an.</p>
    </section>
  </main>
</template>

<style scoped>.link { text-decoration: none; }</style>
