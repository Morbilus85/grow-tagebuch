import { reactive } from 'vue'

export const toast = reactive({ text: '', t: null })
export function say(text) {
  toast.text = text
  clearTimeout(toast.t)
  toast.t = setTimeout(() => (toast.text = ''), 3200)
}

export const fmt = {
  date: (d) => (d ? new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) : '–'),
  dateLong: (d) => (d ? new Date(d).toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' }) : '–'),
  time: (d) => new Date(d).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }),
  dt: (d) => new Date(d).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }),
  // Wassermengen: unter 1 l in ml, sonst Liter mit bis zu 2 Nachkommastellen
  vol: (l) => (l === null || l === undefined ? '–' : l < 1 ? `${Math.round(l * 1000)} ml` : `${Number(l).toLocaleString('de-DE', { maximumFractionDigits: 2 })} l`),
  n: (v, dig = 1) => (v === null || v === undefined || Number.isNaN(v) ? '–' : Number(v).toLocaleString('de-DE', { maximumFractionDigits: dig, minimumFractionDigits: 0 })),
}

export const LOG_TYPES = {
  watering: 'Gießen',
  feeding: 'Düngen',
  measurement: 'Höhe & Abstand',
  observation: 'Beobachtung',
  training: 'Training',
  defoliation: 'Entlauben',
  top_dress: 'Top-Dress',
  foliar: 'Blattspray',
  problem: 'Problem',
  pest: 'Befund',
  treatment: 'Maßnahme',
  note: 'Notiz',
  harvest: 'Ernte',
}

export const rating = { ok: 'ok', grenzwertig: 'warn', schlecht: 'bad', zu_hoch: 'bad', zu_niedrig: 'warn', knapp: 'warn', kritisch: 'bad' }
export const today = () => new Date().toISOString().slice(0, 10)

export const TRAINING = {
  category: { lst: 'Low-Stress-Training', hst: 'High-Stress-Training', schnitt: 'Schnitt', methode: 'Anbaumethoden' },
  stress: { sehr_niedrig: 'kaum Stress', niedrig: 'wenig Stress', mittel: 'mittlerer Stress', hoch: 'hoher Stress' },
  suit: { empfohlen: 'geeignet', bedingt: 'bedingt', abraten: 'ungeeignet' },
  suitClass: { empfohlen: 'ok', bedingt: 'warn', abraten: 'bad' },
  status: { jetzt: 'ok', warten: 'warn', bald: '', vorbei: '', nicht_empfohlen: 'bad' },
}

// Fotos vor dem Hochladen verkleinern (spart Upload-Zeit, umgeht Größenlimits).
// Kann der Browser das Format nicht lesen (z. B. HEIC), geht das Original hoch – der Server wandelt um.
export async function shrinkImage(file, maxPx = 2560, quality = 0.85) {
  try {
    const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' })
    const scale = Math.min(1, maxPx / Math.max(bmp.width, bmp.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bmp.width * scale)
    canvas.height = Math.round(bmp.height * scale)
    canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((res) => canvas.toBlob(res, 'image/jpeg', quality))
    if (!blob) return file
    return new File([blob], (file.name || 'foto').replace(/\.\w+$/, '') + '.jpg', { type: 'image/jpeg' })
  } catch {
    return file
  }
}

export const PEST = {
  status: { offen: 'offen', behandlung: 'in Behandlung', erledigt: 'erledigt' },
  statusClass: { offen: 'bad', behandlung: 'warn', erledigt: 'ok' },
  severity: { 1: 'leicht', 2: 'mittel', 3: 'stark' },
  scope: (c, plants = []) => c.scope === 'zelt' ? 'ganzes Zelt'
    : (c.plant_ids || []).map((id) => plants.find((p) => p.id === id)?.name || `Pflanze ${id}`).join(', ') || 'einzelne Pflanzen',
}
