<script setup>
import { toast } from './util.js'
</script>

<template>
  <nav class="tabs" aria-label="Hauptnavigation">
    <router-link to="/" exact-active-class="router-link-active">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 21V11"/><path d="M12 14c-4 0-7-2.5-7.5-6.5C8.5 7.5 11.5 10 12 14z"/><path d="M12 12c.5-4 3.5-7 7.5-7-.5 4-3.5 7-7.5 7z"/></svg>
      Heute
    </router-link>
    <router-link to="/giessen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5c3 4 5.5 7 5.5 10a5.5 5.5 0 0 1-11 0c0-3 2.5-6 5.5-10z"/></svg>
      Gießen
    </router-link>
    <router-link to="/klima">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 14.5V5a2 2 0 1 1 4 0v9.5a4 4 0 1 1-4 0z"/><path d="M12 11v6"/></svg>
      Klima
    </router-link>
    <router-link to="/licht">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="4" width="16" height="4" rx="1"/><path d="M7 12l-1.5 3M12 12v4M17 12l1.5 3M9.5 19h5"/></svg>
      Licht
    </router-link>
    <router-link to="/mehr">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h10"/></svg>
      Mehr
    </router-link>
  </nav>
  <router-view />
  <div v-if="toast.text" class="toast" role="status">{{ toast.text }}</div>
</template>
