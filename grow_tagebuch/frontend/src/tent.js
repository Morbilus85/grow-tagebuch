// Gewähltes Zelt („Karteikarte“) – gilt für Heute, Gießen, Klima und Licht
import { reactive } from 'vue'
import { api } from './api.js'

const KEY = 'grow.zelt'
function stored() {
  try { return Number(localStorage.getItem(KEY)) || null } catch { return null }
}

export const tent = reactive({ id: stored(), list: [], runs: [], loaded: false })

export function setTent(id) {
  if (!id) return
  tent.id = Number(id)
  try { localStorage.setItem(KEY, String(id)) } catch { /* Speicher nicht verfügbar */ }
}

// Zelte mit Karteikarte: in Betrieb oder mit aktivem Durchgang, nie abgebaute
export async function loadTents() {
  const [setups, runs] = await Promise.all([api.get('setups'), api.get('runs')])
  const active = runs.filter((r) => r.status === 'aktiv')
  tent.runs = active
  tent.list = setups.filter((s) => s.status !== 'abgebaut' && (s.status === 'aktiv' || active.some((r) => r.setup_id === s.id)))
    .map((s) => ({ ...s, run: active.find((r) => r.setup_id === s.id) || null }))
  if (!tent.list.some((s) => s.id === tent.id)) setTent(tent.list[0]?.id || setups[0]?.id)
  tent.loaded = true
  return tent
}

export const current = () => tent.list.find((s) => s.id === tent.id) || null
