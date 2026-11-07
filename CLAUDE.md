# Grow-Tagebuch – Übergabe für neue Sitzungen

Kilians Grow-Tagebuch: organischer Cannabis-Homegrow im Indoor-Zelt, als Home-Assistant-Add-on.
Sprache mit Kilian: Deutsch, direkt, knapp, ehrliche Einschätzungen. Spezifikation: `docs/SPEZIFIKATION.md`.

## Aufbau

- `repository.yaml` + `grow_tagebuch/` = HA-Add-on (config.yaml, build.yaml, Dockerfile, run.sh, DOCS.md, CHANGELOG.md).
  Ingress-Port 8099, liest HA nur (SUPERVISOR_TOKEN → http://supervisor/core/api). Daten in `/data` (SQLite `grow.db`, Fotos).
- Backend `grow_tagebuch/backend/app`: FastAPI + SQLModel (pinned: fastapi 0.115.14, sqlmodel 0.0.24), APScheduler (Klima alle 10 min, Verdichtung 03:17).
  Neue Spalten migriert `db._add_missing_columns` automatisch (nur optionale Felder/Defaults anhängen).
  Logik in `logic/` (phases, feeding, light, space, climate, training), Kataloge `training_data.py`, `germination_data.py`,
  `living_soil_data.py`, `pest_data.py`; Sorten-Recherche `strain_info.py` (Claude-API, Websuche → Structured Outputs).
- Frontend `grow_tagebuch/frontend`: Vue 3 + Vite, Hash-Router, `dist/` wird committed (HA baut ohne Node).
- Tests: `cd grow_tagebuch/backend && python -m pytest -q` (Stand: 38 grün, Stand 0.7.4).

## Release-Ablauf (immer so)

1. Version in `grow_tagebuch/config.yaml` und `backend/app/__init__.py` erhöhen, Eintrag oben in `CHANGELOG.md`.
2. Tests, `cd grow_tagebuch/frontend && npx vite build`.
3. Commit als `git -c user.name="Morbilus85" -c user.email="morbilus@googlemail.com" commit …`, push auf `main`.
4. In HA `ha_manage_app action=check_updates` – **nicht selbst installieren**, Kilian klickt „Aktualisieren“.
5. UI-Änderungen vorher lokal mit Playwright prüfen (Server mit `GROW_DATA_DIR=<scratch>` starten, PID merken – kein `pkill -f`).

## Home Assistant

- Add-on-Slug `a5231e4c_grow_tagebuch`. Live-Daten über `ha_manage_app slug=… path=/api/…` (GET/POST/PATCH/DELETE),
  Logs über `ha_get_logs source=supervisor slug=…`. In `python_transform` kein `|`-Operator.
  HA-Werkzeuge laufen über Kilians Desktop-App (`mcp__remote-devices__Home_Assistant__*`, per ToolSearch laden) – nur
  erreichbar, wenn der Chat in der Desktop-App offen ist. Der Browser-Bereich taugt für HA nicht (lädt nicht).
- Sorten-Recherche (Structured Outputs) läuft gegen die echte API – bestätigt am 07.11.2026 (Blueberry Automatic).
  Ab 0.7.4: `seed_to_harvest_days`/`flowering_days`/`max_height_cm` = realistische Grower-Werte (Rechengrundlage),
  Breeder-Angaben stehen in `info.breeder_values`. Steckbrief zeigt „App rechnet mit“.
- Regeln: App liest HA nur, schaltet nie. Automationen „Growzelt-Heizung“ und „Heizmatte“ hat Kilian bewusst deaktiviert –
  nicht ohne Rückfrage aktivieren. Neue HA-Automationen nur deaktiviert anlegen; größere Änderungen vorher vorschlagen.
- Sensoren: Zelt `sensor.homegrow_probe_sensor_sonden_*` (Temperatur, Luftfeuchtigkeit, VPD), Lampe Stufe
  `sensor.homegrow_port_2_aktuelle_leistung`, Lampe an/aus `binary_sensor.homegrow_port_2_zustand`, Abluft Port 1,
  Heizung `switch.steckdose_growzelt_heizung`, Heizmatte `switch.steckdose_heizmatte`, Raum `sensor.sensor_display_grow_room_*`.
- Claude-API-Schlüssel steht in der Add-on-Konfiguration (`anthropic_api_key`), nie im Code. Schlüssel ist auf Workspace „Default“ beschränkt.

## Setup (Stand 01.11.2026)

- Zelt ca. 80×80×180, AC-Infinity-Controller, Lampe Ionframe EVO4 (Stufen 1–10, Port 2), Lichtplan 20/4 für Autos,
  Lichtkalibrierung in `docs/messungen/licht_ionframe_evo4.csv`. Stufe 3, 60 cm.
- 20-l-Stofftöpfe, Floragard Grow Mix Organic + 10–20 % BioBizz Wurmhumus, Pflanzloch mit Light-Mix. Leitungswasser Essen
  (EC 0,47, pH 7,9). Nur organisch, BioBizz + eigene Zusätze. Haushalt 3 Erwachsene → KCanG-Limit 9 Pflanzen.

## Aktueller Stand der Daten

- Durchgang 3 „White Truffle Auto + Blueberry Auto – Herbst 2026“ (ID 3, aktiv, Lampe Stufe 3 / 60 cm, 20/4 ab 06:00):
  - Pflanze 1 (ID 7): White Truffle Auto (Strain-ID 2), eingeweicht 31.10. 23:10, gesetzt 01.11., aufgelaufen 03.11.2026.
  - Pflanze 2 (ID 8) „Keimt nicht“ und Pflanze 3 (ID 9) „Keimling eingegangen“: am 07.11.2026 abgebrochen.
  - Pflanze 4 + 5 (ID 10/11): Blueberry Automatic (Zamnesia, Strain-ID 3), Nachzügler, 3 Blueberry-Samen Reserve, H2O2 eingeweicht
    07.11.2026 17:03/17:05, noch nicht gesetzt. Strain 3 von Hand auf 70 Tage / 95 cm gesetzt. Plan: erst mit Keimwurzel 0,5–1 cm setzen, je Topf den schwächeren später abbrechen.
  - Keine White-Truffle-Samen mehr vorrätig.
- Durchgang 1 „Strawberry Cough Auto – Herbst 2026“: abgebrochen (zu tief gesetzt, kein Trieb), bleibt als Verlauf.
- Schädlingsfall 1 Trauermücken (zeltweit, in Behandlung, Nematoden bestellt), hängt an Durchgang 3.
- Aufgaben: pH-Meter kalibrieren (14 d), Gelbtafeln prüfen (7 d), Töpfe drehen (7 d).

## Offen

- 0.7.4 bereitgestellt (realistische Sortenwerte). Nach dem Update Strain 2 (White Truffle) und 3 (Blueberry) per
  „Infos aus dem Internet holen“ neu recherchieren und Werte prüfen.
- Dosierungen von den Etiketten nachtragen, sobald Kilian Fotos schickt (DiMikro, Rootmax, Ackerschachtelhalm,
  Brennnesselpulver, Aloe-Puder, Neem Cake, CalMag).
- Phase 1b (ntfy-Push, Topfgewicht lernen, Export) und Phase 2 (KI-Klimacheck, freie Frage) – vorgeschlagen, nicht gestartet.
