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
  pest: 'Schädlinge',
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
