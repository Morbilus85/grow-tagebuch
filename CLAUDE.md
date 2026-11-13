# Grow-Tagebuch – Übergabe für neue Sitzungen

Kilians Grow-Tagebuch: organischer Cannabis-Homegrow im Indoor-Zelt, als Home-Assistant-Add-on.
Sprache mit Kilian: Deutsch, direkt, knapp, ehrliche Einschätzungen. **Alles selbst und automatisch ausführen**
(Releases, Updates, Daten in der App) – nicht nachfragen, nicht an Kilian delegieren. Ausnahme: HA-Regeln unten. Spezifikation: `docs/SPEZIFIKATION.md`.

## Aufbau

- `repository.yaml` + `grow_tagebuch/` = HA-Add-on (config.yaml, build.yaml, Dockerfile, run.sh, DOCS.md, CHANGELOG.md).
  Ingress-Port 8099, liest HA nur (SUPERVISOR_TOKEN → http://supervisor/core/api). Daten in `/data` (SQLite `grow.db`, Fotos).
- Backend `grow_tagebuch/backend/app`: FastAPI + SQLModel (pinned: fastapi 0.115.14, sqlmodel 0.0.24), APScheduler (Klima alle 10 min, Verdichtung 03:17).
  Neue Spalten migriert `db._add_missing_columns` automatisch (nur optionale Felder/Defaults anhängen).
  Push über ntfy in `notify.py` (Einstellungen in Setting `notify`, Fallback Add-on-Optionen; Job alle 5 min für die
  tägliche Aufgabenliste, Klima-Alarm hängt am Klima-Job; Alarm-Zustand nur im Speicher). API `GET/PUT /api/notify`, `POST /api/notify/test` (`kind=tasks`).
  Logik in `logic/` (phases, feeding, light, space, climate, training), Kataloge `training_data.py`, `germination_data.py`,
  `living_soil_data.py`, `pest_data.py`; Sorten-Recherche `strain_info.py` (Claude-API, Websuche → Structured Outputs).
  Erde/Wasser-Recherche `material_info.py` (nutzt `_research`/`_extract` aus strain_info): `POST /api/waters/{id}/refresh`
  `{city}` überschreibt Wasserwerte (EC in mS/cm, Versorger-Analyse), `POST /api/soils/{id}/refresh` `{product}` füllt nur
  `info` – Düngeplan-Felder (Wochen, Schema-Typ) ändert nur Kilian per „Übernehmen“. Beide laufen über `_shielded` weiter,
  wenn HA-Ingress trennt (Logs „Wasser-/Erde-Recherche für … gespeichert“). `GET /api/ai/status`.
- KI-Begutachtung/Fragen (0.12.0) in `ai_chat.py`, Modell `claude-opus-5-5` (Preise in `PRICE`), Modelle `AiChat`/`AiMessage`.
  Nur auf Knopfdruck, nie automatisch pro Foto (Kilians Wunsch). `kind=check` (Pflanze, Fotos) oder `frage` (Pflanze oder
  Zelt). Kontext-Snapshot beim Start (`build_context`: Phase, Logs 21 d, Klima 7 d, Erde/Wasser/Lampe, Fälle, Inventar,
  Fazit + Foto des letzten Checks), danach Chat mit Rückfragen; Verlauf per Prompt-Caching. Jede Antwort Structured
  Outputs (`SCHEMA`: reply, ampel, findings, next_steps, comparison, photo_requests, suggestions, summary). Antwort läuft
  im Hintergrund, Frontend pollt `GET /api/ai/chats/{id}` (`busy`). API: `POST /api/ai/chats`, `…/messages`, `…/photos`
  (Foto landet als Beobachtung im Tagebuch), `…/apply` (Vorschlag → Aufgabe/Notiz), `…/retry`, `DELETE`. Check erzeugt
  Log-Typ `ai_check` (Text = Ampel + Fazit, Tag `ai_chat:<id>`). Keine Websuche im Chat (Structured Outputs). KI ändert
  nie selbst etwas. Frontend `/ki/neu?pflanze=…[&art=frage]` bzw. `?zelt=…`, Chat `/ki/:id`.
- Frontend `grow_tagebuch/frontend`: Vue 3 + Vite, Hash-Router, `dist/` wird committed (HA baut ohne Node).
  „Mehr“ (seit 0.10.0) = nur Kachel-Menü in Gruppen; Unterseiten `/mehr/durchgaenge`, `/mehr/sorten`, `/mehr/aufgaben`,
  `/mehr/erde-wasser` (Erde + Wasser bewusst zusammen), `/mehr/zelte` (Zelte + Sensoren je Zelt),
  `/mehr/einstellungen` (Push, Haushalt, Export).
  Mehrere Zelte (0.11.0): `Setup` = Zelt mit `medium` (erde|rdwc), `status` (geplant|aktiv|abgebaut), `lamp`; `POST /api/setups`.
  Klima `/klima?zelt=<setup_id>`, Licht `/licht?run=<run_id>` mit Umschalter. Lichtmodell nur aus Messpunkten des eigenen
  Zelts (kein Rückfall auf Ionframe). Eigene Produkte: Key `custom_…`, nur diese per `DELETE /api/products/{id}` löschbar;
  sie tauchen im Gieß-Assistent nur auf, wenn ein Düngeschema ihren Key enthält.
  Neue Bereiche als eigene Kachel/Seite anlegen, nicht wieder alles auf eine Seite.
  Datei-Inputs nie mit `multiple`: Die HA-Android-App liefert bei Mehrfachauswahl aus der Galerie eine leere Liste
  (bis 0.11.0 kam so kein einziges Foto an). Einzeln wählen, Vorschau zeigen; Uploads loggen „Foto … gespeichert“.
- Tests: `cd grow_tagebuch/backend && python -m pytest -q` (Stand: 48 grün, Stand 0.12.0). KI-Test heißt `test_zz_ai_chat.py`,
  damit er nach `test_flow` läuft (gemeinsame Test-DB).

## Release-Ablauf (immer so)

1. Version in `grow_tagebuch/config.yaml` und `backend/app/__init__.py` erhöhen, Eintrag oben in `CHANGELOG.md`.
2. Tests, `cd grow_tagebuch/frontend && npx vite build`.
3. Commit als `git -c user.name="Morbilus85" -c user.email="morbilus@googlemail.com" commit …`, push auf `main`.
4. In HA `ha_manage_app action=check_updates`, dann `action=update` – **selbst installieren** (Kilians Wunsch seit 07.11.2026).
   Folgeschritte (z. B. Sorten neu recherchieren) ebenfalls selbst über die API erledigen, nicht an Kilian delegieren.
5. UI-Änderungen vorher lokal mit Playwright prüfen (Server mit `GROW_DATA_DIR=<scratch>` starten, PID merken – kein `pkill -f`).

## Home Assistant

- Add-on-Slug `a5231e4c_grow_tagebuch`. Live-Daten über `ha_manage_app slug=… path=/api/…` (GET/POST/PATCH/DELETE),
  Logs über `ha_get_logs source=supervisor slug=…`. `POST /api/strains/{id}/refresh` dauert ca. 1 min →
  Proxy-Timeout nach 30 s ist normal, läuft weiter; Log „Sorten-Recherche für … gespeichert“ abwarten, dann `GET /api/strains` prüfen (`info.updated_at`). In `python_transform` kein `|`-Operator.
  HA-Werkzeuge laufen über Kilians Desktop-App (`mcp__remote-devices__Home_Assistant__*`, per ToolSearch laden) – nur
  erreichbar, wenn der Chat in der Desktop-App offen ist. Der Browser-Bereich taugt für HA nicht (lädt nicht).
- Sorten-Recherche (Structured Outputs, Websuche max. 3): **nur Breeder-Angaben** (Kilians Entscheidung 07.11.2026),
  Seedfinder nur als Ersatz für fehlende Breeder-Punkte. Grower-/Forenwerte, Mitteln und Nachrecherche (0.7.4–0.7.11)
  wurden in 0.8.0 bewusst wieder entfernt – nicht erneut einbauen. Realistischere Werte trägt Kilian ggf. von Hand ein.
- Regeln: App liest HA nur, schaltet nie. Automationen „Growzelt-Heizung“ und „Heizmatte“ hat Kilian bewusst deaktiviert –
  nicht ohne Rückfrage aktivieren. Neue HA-Automationen nur deaktiviert anlegen; größere Änderungen vorher vorschlagen.
- Sensoren: Zelt `sensor.homegrow_probe_sensor_sonden_*` (Temperatur, Luftfeuchtigkeit, VPD), Lampe Stufe
  `sensor.homegrow_port_2_aktuelle_leistung`, Lampe an/aus `binary_sensor.homegrow_port_2_zustand`, Abluft Port 1,
  Heizung `switch.steckdose_growzelt_heizung`, Heizmatte `switch.steckdose_heizmatte`, Raum `sensor.sensor_display_grow_room_*`.
- ntfy: Topic `grow_HA_Tagebuxh_App` auf ntfy.sh (so von Kilian vorgegeben, in der App gespeichert). Aufgaben täglich 08:00,
  Klima-Alarm Standard (deutliche Abweichung > 30 min, Wiederholung 3 h), Sensor-Ausfall 30 min. Kein HA-Notify – App bleibt lesend.
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
    07.11.2026 17:03/17:05, noch nicht gesetzt. Plan: erst mit Keimwurzel 0,5–1 cm setzen, je Topf den schwächeren später abbrechen.
  - Keine White-Truffle-Samen mehr vorrätig.
- Durchgang 1 „Strawberry Cough Auto – Herbst 2026“: abgebrochen (zu tief gesetzt, kein Trieb), bleibt als Verlauf.
- Schädlingsfall 1 Trauermücken (zeltweit, in Behandlung, Nematoden bestellt), hängt an Durchgang 3.
- Aufgaben: pH-Meter kalibrieren (14 d), Gelbtafeln prüfen (7 d), Töpfe drehen (7 d).

## Offen

- Zweites Zelt (Abstellraum): Homebox 100×100×200 fest, Lampe Spider Farmer SE5000, wahrscheinlich RDWC (Fertigsystem,
  2 Plätze, mineralisch, keine Osmose; Leitungswasser-EC ca. 0,44). Rest noch nicht gekauft. In der App als Zelt
  „geplant“ anlegen. RDWC-Teil bauen, sobald System + Dünger feststehen: Reservoir-Log (Wechsel/Nachfüllen, l, EC, pH,
  Wassertemp.), Zielbereiche (pH 5,8–6,2, EC je Phase minus Grund-EC, Wasser 18–20 °C), Aufgaben, Push > 22 °C Wassertemp.,
  Wassertemperatur-Sensor in HA vorsehen. SE5000 braucht eigene Lichtkalibrierung.

- Dosierungen von den Etiketten nachtragen, sobald Kilian Fotos schickt (DiMikro, Rootmax, Ackerschachtelhalm,
  Brennnesselpulver, Aloe-Puder, Neem Cake, CalMag).
- Phase 1b: ntfy-Push erledigt (0.9.0). Topfgewicht-Lernen bewusst erst beim nächsten Durchgang (Kilian 08.11.2026:
  Erde schon feucht, keine Waage; dann Topf mit trockener Erde vor dem ersten Gießen wiegen). Export (CSV) offen.
- Phase 2: Foto-Check + freie Frage erledigt (0.12.0). Offen: KI-Düngeempfehlung gegen Regel-Rezept, Erntefenster
  (Trichome), ggf. Websuche im Chat. Zeltweiter Foto-Check aller Pflanzen bewusst nicht (Kilian 13.11.2026).
