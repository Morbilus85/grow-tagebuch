import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base './' – alle Pfade relativ, damit die App hinter Home-Assistant-Ingress funktioniert
export default defineConfig({
  base: './',
  plugins: [vue()],
  server: { proxy: { '/api': 'http://127.0.0.1:8099' } },
  build: { outDir: 'dist', assetsDir: 'assets', chunkSizeWarningLimit: 800 },
})
