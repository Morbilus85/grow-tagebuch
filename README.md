# Grow-Tagebuch

Home-Assistant-Add-on: Tagebuch für organische Grows mit Düngeassistent auf BioBizz-Basis, Fotos, Klima aus Home Assistant und Lichtplanung aus eigener PAR-Messung.

## Installation

1. Home Assistant → **Einstellungen → Add-ons → Add-on-Store**
2. Oben rechts **⋮ → Repositories** → `https://github.com/Morbilus85/grow-tagebuch` hinzufügen
3. **Grow-Tagebuch** installieren, starten, „In Seitenleiste anzeigen“ aktivieren

Updates erscheinen danach automatisch im Add-on-Store.

## Aufbau

- `grow_tagebuch/backend` – FastAPI, SQLite, Regel-Engine (Düngung, Licht, Phasen, Platz)
- `grow_tagebuch/frontend` – Vue-App; `dist/` ist vorgebaut, damit Home Assistant beim Installieren kein Node braucht
- `docs/SPEZIFIKATION.md` – Funktionsumfang und Regeln
- `docs/messungen/` – Lichtkalibrierung

## Entwicklung

```sh
cd grow_tagebuch/backend
pip install -r requirements.txt pytest
GROW_DATA_DIR=./.data python -m uvicorn app.main:app --port 8099   # API + gebaute Oberfläche
python -m pytest tests

cd ../frontend && npm install && npm run dev   # Oberfläche mit Proxy auf :8099
```

Für Sensordaten außerhalb des Add-ons `HA_URL` und `HA_TOKEN` (Long-Lived Token) setzen.
