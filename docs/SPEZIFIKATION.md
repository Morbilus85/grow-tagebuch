# Grow-Tagebuch – Spezifikation

Stand: 27.10.2026 · Version 0.1 (Entwurf zur Freigabe)

## 1. Ziel

Ein Home-Assistant-Add-on, das organische Cannabis-Grows (Indoor-Zelt und Hochbeet) vollständig dokumentiert und daraus konkrete Handlungsanweisungen ableitet: Gießen, Düngen, Zusätze, Licht und Klima, angepasst an Pflanze, Phase, Erde und Wasser.

Leitprinzipien:

- **Herstellerschema ist die Basis, nicht die KI.** Düngeschemata liegen strukturiert und mit Quelle in der Datenbank. Regeln und später die KI passen sie an, erfinden aber keine Dosierungen.
- **Organisch zuerst.** Der pH-Wert und das Pflanzenbild steuern. EC wird geloggt, aber nur als Trend genutzt.
- **Konservativ starten.** Vorgedüngte Erde plus Wurmhumus plus Neem Cake: Überdüngung ist am Anfang das größere Risiko als Mangel.
- **Nur lesend auf Home Assistant.** Die App liest Sensoren, schaltet aber nichts. Steuerungsvorschläge gibt es höchstens als Vorschlag.

## 2. Betrieb und Architektur

| Thema | Entscheidung |
|---|---|
| Laufzeit | HA-Add-on auf dem Mini-PC (amd64), Docker-Image aus diesem Repo |
| Aufruf | HA-Seitenleiste über Ingress („Grow-Tagebuch“), auch in der HA-Companion-App auf dem Handy |
| Backend | Python 3.12, FastAPI, SQLAlchemy/SQLModel, Alembic-Migrationen |
| Datenbank | SQLite unter `/data/grow.db` |
| Fotos | `/data/photos/…`, beim Upload auf max. 2560 px verkleinert, Original optional |
| Frontend | Vue 3 + Vite, mobil zuerst, als statische Dateien vom Backend ausgeliefert |
| Hintergrundjobs | APScheduler im Backend (Klima-Aufzeichnung, Erinnerungen) |
| Backup | Alles liegt in `/data` und ist damit automatisch Teil der HA-Backups |
| Extern | Claude API (Phase 2), ntfy (Erinnerungen). Sonst keine Cloud. |
| Updates | Versionsnummer in `config.yaml` erhöhen → Update-Knopf im HA-Add-on-Store |

**Ehrliche Korrektur zur „App auf dem Homescreen“:** Eine echte installierbare PWA braucht HTTPS. Solange HA nur per `http://` im Heimnetz läuft, ist der beste Weg die **HA-Companion-App** (Grow-Tagebuch in der Seitenleiste). Sobald Nabu Casa oder Tailscale mit HTTPS eingerichtet ist, funktioniert auch die eigenständige Homescreen-App. Kamera-Upload funktioniert in beiden Fällen.

### Add-on-Konfiguration (in HA einstellbar)

- `anthropic_api_key` (Phase 2)
- `ntfy_server` (Standard `https://ntfy.sh`), `ntfy_topic`
- `climate_interval_minutes` (Standard 10)
- Sensor-Zuordnung pro Setup erfolgt in der App selbst, nicht in der Add-on-Config

## 3. Vorhandene Home-Assistant-Daten (geprüft am 27.10.2026)

Bereich **Grow-Zelt**, AC-Infinity-Integration („Homegrow“):

| Zweck | Entität | Hinweis |
|---|---|---|
| Temperatur (Sonde, Kronendach) | `sensor.homegrow_probe_sensor_sonden_temperatur` | Hauptquelle |
| Luftfeuchte (Sonde) | `sensor.homegrow_probe_sensor_sonden_luftfeuchtigkeit` | Hauptquelle |
| VPD (Sonde) | `sensor.homegrow_probe_sensor_sonden_vpd` | Wird zusätzlich selbst berechnet (Blatt-Offset) |
| Temperatur/Feuchte/VPD (Controller) | `sensor.homegrow_controller_*` | Zweitquelle |
| Abluft | `binary_sensor.homegrow_port_1_status`, `sensor.homegrow_port_1_aktuelle_leistung` | Port 1 |
| Lampe (Ionframe EVO4) | `binary_sensor.homegrow_port_2_status`, `sensor.homegrow_port_2_aktuelle_leistung` | Port 2, Stufe 1–10 |
| Heizmatte | `switch.steckdose_heizmatte`, `sensor.steckdose_heizmatte_power` | Bereich nicht zugewiesen |
| Zusatzheizung | `switch.steckdose_growzelt_heizung`, `sensor.steckdose_growzelt_heizung_power` | |
| Raumklima Grow Room | `sensor.sensor_display_grow_room_temperature`, `…_humidity` | Umgebung außerhalb des Zelts |

Die Einstellungs-Entitäten des Controllers (Zielwerte, Modi pro Port) stehen alle auf `unknown`. Für eine reine Lese-App spielt das keine Rolle.

**Warum die App Klimadaten selbst speichert:** Der HA-Recorder löscht Verläufe standardmäßig nach 10 Tagen. Ein Run dauert 10–16 Wochen. Die App speichert deshalb alle `climate_interval_minutes` einen Messpunkt und verdichtet nach 14 Tagen auf Stundenmittel (min/max/mittel).

## 4. Datenmodell

```
Setup ─┬─ Equipment (n)
       ├─ SensorMapping (n)        Rolle → HA-Entität
       └─ Run (n) ─┬─ Plant (n) ─┬─ PhaseEvent (n)
                   │             ├─ LogEntry (n) ─┬─ WateringDetail (0..1)
                   │             │                ├─ ProductUse (n)
                   │             │                └─ Photo (n)
                   │             └─ Recommendation (n)        (Phase 2)
                   ├─ SoilProfile (1)
                   ├─ WaterProfile (1)
                   └─ LightSchedule (n, zeitlich)
Product (Inventar) ── ScheduleEntry ── FeedingSchedule
ClimateSample (Setup, Zeit)
Reminder
```

### Entitäten im Detail

- **Setup**: Name, Typ (Zelt / Hochbeet / Freiland), Maße, Standort (indoor/outdoor), Notizen.
- **Equipment**: Kategorie (Zelt, Licht, Abluft, Filter, Umluft, Controller, Heizmatte, Heizung, Befeuchter, Entfeuchter, Topf, Messgerät, Sonstiges), Hersteller, Modell, technische Daten als JSON (z. B. Licht: Watt, Dimmstufen, Chip; Abluft: m³/h; Topf: Liter, Material).
- **SensorMapping**: Rolle (`temp`, `rh`, `vpd`, `light_power`, `exhaust_power`, `heater_switch`, `heatmat_switch`, `room_temp`, `room_rh`) → HA-Entität.
- **SoilProfile**: Name, Bestandteile mit Anteil (z. B. Floragard Grow Mix Organic 85 %, BioBizz Worm-Humus 15 %), `prefertilized_weeks` (Standard 4), Zuordnung zu einem Schema-Typ (`all_mix` = vorgedüngt / `light_mix` = schwach gedüngt), eingemischte Amendments mit Menge und Datum.
- **WaterProfile**: Quelle (Leitungswasser/Regen/Osmose/Mischung), EC, pH, Ca, Mg, Na, Cl, SO₄, Säurekapazität, Gesamthärte, Messdatum, Quelle/URL. Eigene Messungen überschreiben die Analyse.
- **Product**: Name, Marke, Art (`base` Grunddünger, `stimulant` Booster/Stimulator, `root`, `microbial` Bodenleben, `carbs` Mikrobenfutter, `amendment` Einmischen/Top-Dress, `plant_protection` Stärkung/Schutz, `ph`, `calmag`), Form (flüssig/Pulver), NPK (falls angegeben), Etikett-Dosierung (min/max pro Liter oder pro Liter Erde), Anwendungsart (Gießen/Blattspray/Einmischen/Top-Dress), **Phasenregeln** (erlaubt / gesperrt / nur Spray bis Blüte W2 …), **Wirkgruppe** für Doppelungswarnung, „vorhanden“ ja/nein, Füllstand optional.
- **FeedingSchedule / ScheduleEntry**: Hersteller, Version/Jahr, Quell-URL, Schema-Typ, Abrufdatum. Einträge: Stufe (`seedling`, `veg`, `bloom_1` … `bloom_8`, `flush`), Produkt, Dosis pro Liter.
- **Strain**: Name, Breeder, Auto/Photo, Breeder-Angabe Samen-bis-Ernte bzw. Blütedauer, Notizen.
- **Run**: Setup, Erde, Wasser, Startdatum, Status (geplant/aktiv/Ernte/Trocknung/Curing/abgeschlossen), Ernte- und Trockengewicht.
- **Plant**: Run, Sorte, Name/Nummer, Topfgröße, Keimmethode, Datum eingeweicht, Datum gesetzt, Datum aufgelaufen, Status, aktueller Stärkefaktor Düngung (0,0–1,0).
- **PhaseEvent**: Phase + Datum + Quelle (geschätzt/bestätigt).
- **LogEntry**: Zeitpunkt, Typ (`watering`, `feeding`, `foliar`, `top_dress`, `training`, `defoliation`, `observation`, `problem`, `measurement`, `harvest`), Freitext, Tags.
- **WateringDetail**: Menge (l), pH rein, EC rein, Runoff-Menge, pH Runoff, EC Runoff, Topfgewicht vorher/nachher (optional).
- **ProductUse**: Produkt, Menge gesamt und pro Liter, Anwendungsart.
- **Photo**: Datei, Aufnahmezeit, Pflanze, Tags (Gesamtbild, Blatt, Trichome, Problem).
- **LightSchedule**: Stunden an/aus, Startzeit, Dimmstufe, Höhe in cm, ab Datum.
- **ClimateSample**: Setup, Zeitstempel, Temp, RH, VPD (Luft und Blatt), Lampenleistung, Heizung/Heizmatte an.
- **Reminder**: Typ, Fälligkeit, Wiederholung, Bezug (Pflanze/Run), erledigt.

## 5. Funktionen Phase 1 – Grundgerüst

### 5.1 Stammdaten
- Setups mit Equipment anlegen; vorbefüllt mit dem Zelt-Setup aus der AC-Infinity-Bestellung (Cloudlab 733, Ionframe EVO4, Cloudline Pro S6, Aktivkohlefilter, Cloudray S6, Controller AI+, 19-l-Stofftöpfe) plus Heizmatte und Zusatzheizung.
- Zweites Setup „Hochbeet Garten“ (ca. 100 l, Ost/Nordost) als Vorlage.
- Erdprofile, Wasserprofile, Sorten, Inventar.

### 5.2 Runs und Pflanzen
- Run anlegen, Pflanzen hinzufügen, Fotos und Logs pro Pflanze oder für den ganzen Run.
- **Phasenmodell Auto**: Keimung → Sämling (bis ca. Tag 14) → Wachstum → Vorblüte → Blüte W1…Wn → Reife/Spülen → Ernte → Trocknung → Curing. Übergänge werden anhand der Breeder-Angabe **geschätzt**, ab „Vorblüte bestätigt“ (Knopf) wird die Blütezeit daran verankert.
- **Phasenmodell Photo**: Wachstum unbegrenzt, Blüte ab Umstellungsdatum 12/12.
- Zähler: Tag seit Keimung, Woche im Plan, Tage bis voraussichtliche Ernte.

### 5.3 Tagebuch
- Schnell-Log (ein Knopf je Typ), Foto direkt von der Handykamera, mehrere Fotos pro Eintrag.
- Zeitstrahl pro Pflanze: Fotos, Einträge und Klimakurve übereinander.

### 5.4 Gieß- und Düngeassistent (regelbasiert)
Ablauf: Pflanze(n) wählen → Wassermenge eingeben → App erzeugt das Rezept → bestätigen → wird automatisch geloggt.

Berechnung:

1. **Basis-Schema** nach Schema-Typ der Erde. Floragard Grow Mix Organic + Wurmhumus ist vorgedüngt → **BioBizz-All-Mix-Tabelle** als Basis.
2. **Stufen-Zuordnung für Autos**: Woche 1–2 nach Keimung nur Wasser (+ optional Root-Juice laut Schema), danach Spalte „Wachstum“, ab Vorblüte Blüte W1. Die acht Blüte-Spalten werden auf die tatsächliche Blütedauer der Sorte gestreckt oder gestaucht; die letzte Woche vor Ernte ist nur Wasser.
3. **Vorgedüngte Erde**: In den ersten `prefertilized_weeks` (+1 Woche bei ≥10 % Wurmhumus) keine Grunddünger (Bio-Grow/Bio-Bloom), danach Einstieg mit Stärkefaktor 0,5, Steigerung um 0,25 pro Woche bis 1,0, solange keine Warnzeichen geloggt sind.
4. **Ersetzungen**: Fish-Mix → Bio-Grow; Alg-A-Mic und Microbes fehlen im Inventar → entfallen bzw. DiMikro nach Etikett als Bodenleben-Ersatz.
5. **Stärkefaktor pro Pflanze**: Basisdosis × Faktor. Regeln senken ihn (Blattspitzen verbrannt, „Klauen“, sehr dunkles Grün → −25 %) oder erlauben Steigerung (Aufhellen unterer Blätter in Wachstum → +25 %, max. 1,0). Über 1,0 nur nach ausdrücklicher Bestätigung.
6. **Wasserkorrektur**: Essen ist weiches Wasser (Ca 39 mg/l, Mg 7,6 mg/l). Laut BioBizz wird bei weichem Wasser CalMag ergänzt → CalMag wird ab Wachstum standardmäßig vorgeschlagen, Dosis laut Etikett, in der ersten Hälfte der Stufe mit halber Dosis.
7. **pH**: Ziel 6,2–6,8 (Erde). Bio-Down wird nicht pauschal dosiert, sondern aus deinen eigenen Messungen gelernt: Die App merkt sich „x ml Bio-Down pro 10 l bei Rezept y → pH z“ und schlägt beim nächsten Mal die gelernte Menge vor.
8. **EC**: Leitungswasser-EC (0,47) wird abgezogen und gesondert angezeigt. Runoff-EC wird als Trend dargestellt; steigt er über mehrere Gießungen deutlich, gibt es einen Hinweis, aber keine automatische Reduktion.
9. **Gießmenge**: Sämling nur im Ring um die Pflanze (0,1–0,3 l), danach nach Topfgewicht oder Erfahrungswert. Bei organischer Erde ist Runoff optional.

### 5.5 Regeln für Zusätze (Warnungen und Sperren)

| Regel | Wirkung |
|---|---|
| Root-Juice und Rootmax in derselben Woche | Warnung „gleiche Wirkgruppe“ |
| Acti-Vera und Aloe-Vera-Puder gleichzeitig | Warnung „gleiche Wirkgruppe“ |
| Brennnesselpulver/-sud ab Blüte W2 | Warnung (stickstofflastig) |
| Neemöl als Blattspray ab Vorblüte | gesperrt |
| Blattspray allgemein ab Blüte W3 | gesperrt (BioBizz: Blattdüngung nur bis Blüte W2) |
| Blattspray bei Licht an | Warnung (Brennglas, Spray nur kurz vor Licht aus) |
| Melasse/Backmalz | erst ab Blüte, niedrige Dosis, mit Hinweis auf Schimmel-/Trauermückenrisiko bei Übermaß |
| Grunddünger bei frisch vorgedüngter Erde | gesperrt bis Ende `prefertilized_weeks` |
| Top-Dress (Neem Cake, Wurmhumus, Urgesteinsmehl …) | eigener Log-Typ, wirkt laut Regel mehrere Wochen, senkt den Stärkefaktor beim nächsten Gießen |

### 5.6 Klima
- Live-Anzeige Temperatur, Feuchte, VPD mit Ampel nach Zielbereich der aktuellen Phase.
- Zielbereiche VPD (Richtwerte, editierbar): Sämling 0,4–0,8 kPa · Wachstum 0,8–1,2 · Blüte 1,0–1,5 · späte Blüte 1,2–1,6.
- Verlaufsdiagramm pro Run (Tag/Woche/gesamt), Tag-/Nachtwerte getrennt anhand des Lichtplans.

### 5.7 Licht
- Lichtplan pro Run (Autos Standard 20/4, editierbar), Stufe 1–10, Höhe.
- Lichtzeiten und aktuelle Stufe werden aus Port 2 des Controllers gelesen.
- Ziel-PPFD nach Phase (Sämling 200–300, Wachstum 400–600, Blüte 700–900 µmol/m²/s) und daraus DLI.
- AC Infinity veröffentlicht für die Ionframe EVO4 keine PPFD-Karte nach Höhe. Deshalb **Kalibrierung**: Du misst einmal (z. B. mit der App „Photone“ oder einem PAR-Meter) bei 2–3 Höhen/Dimmstufen, die App interpoliert. Ohne Kalibrierung gibt es nur vorsichtige Standardwerte.

### 5.8 Erinnerungen (ntfy)
- Gießen prüfen, Düngetag, nächste Phase/erwarteter Übergang, Dimmstufe erhöhen, Top-Dress fällig, Produkt fast leer, Fotodokumentation (z. B. jeden 3. Tag).

### 5.9 Seed-Daten bei Installation
- Equipment aus der Bestellung, Erdprofil „Floragard Grow Mix Organic + 10–20 % Wurmhumus“, Wasserprofil „Essen Leitungswasser (Q4/2025)“, Inventar (siehe Anhang), BioBizz-Schema All-Mix und Light-Mix, Run „Strawberry Cough Auto – Herbst 2026“ mit Einweichen am 26.10.2026. Sorte: Zamnesia Seeds, Strawberry Fields × Haze × Ruderalis, ca. 10–11 Wochen Samen bis Ernte, bis ca. 120 cm. Lichtkalibrierung aus `docs/messungen/licht_ionframe_evo4.csv`.

## 6. Phase 2 – KI-Schicht (Claude API)

- **Düngeempfehlung**: Die App schickt Claude ein Paket aus Schema-Auszug, Rezept-Vorschlag der Regel-Engine, Erde, Wasser, Phase, letzten 5–10 Logs, Klima-Zusammenfassung und optional Fotos. Claude gibt **strukturiertes JSON** zurück: Anpassungen gegenüber dem Regel-Rezept mit Begründung. Die App prüft das Ergebnis gegen harte Grenzen (Etikett-Maximum, Sperrregeln) und zeigt es nur an, wenn es diese einhält.
- **Foto-Diagnose**: Blatt- oder Pflanzenfoto + Kontext → Einschätzung (Mangel, Überdüngung, pH-Problem, Schädlinge, Lichtstress, Hitze) mit Sicherheit und konkreten nächsten Schritten.
- **Erntefenster**: Trichom-Makrofotos + Breeder-Angabe.
- **Schema-Aktualisierung**: Claude kann neue Herstellerschemata recherchieren und als Entwurf importieren; du bestätigst vor der Übernahme.
- Jede Empfehlung wird mit Eingabe-Snapshot gespeichert (nachvollziehbar, auswertbar).
- Kosten: bei ein paar Abfragen pro Woche mit Fotos realistisch im niedrigen Euro-Bereich pro Monat.

## 7. Phase 3 – Abschluss und Auswertung

- Ernte (Nassgewicht), Trocknung (Klima, Gewichtsverlauf bis ca. 60–65 % Gewichtsverlust), Curing (Gläser, Feuchte, Burping-Erinnerungen).
- Run-Vergleich: Ertrag pro Watt und pro Pflanze, Dauer, Klima-Durchschnitt, Düngermenge gesamt, Probleme.
- KCanG-Übersicht: Anzahl gleichzeitig lebender Pflanzen, Erntemenge.

## 8. Bildschirme

1. **Heute**: alle aktiven Pflanzen mit Phase, Tag, nächster Aktion, Klima-Ampel, Knöpfe „Gießen“, „Foto“, „Notiz“.
2. **Pflanze**: Zeitstrahl, Fotos, Klimakurve, Phasen, Stärkefaktor.
3. **Gieß-Assistent**: Rezept, Warnungen, Bestätigen → Log.
4. **Run**: Übersicht, Lichtplan, Klima, Kosten/Verbrauch.
5. **Stammdaten**: Setups & Equipment, Erde, Wasser, Inventar, Sorten, Schemata.
6. **Einstellungen**: Sensor-Zuordnung, Zielbereiche, Erinnerungen, Export (JSON/CSV).

## 9. Repo-Struktur

```
grow-tagebuch/
├── repository.yaml            HA-Add-on-Repository
├── grow_tagebuch/             das Add-on
│   ├── config.yaml
│   ├── Dockerfile
│   ├── backend/               FastAPI-App, Regel-Engine, Migrationen, Seeds
│   └── frontend/              Vue-App
├── docs/SPEZIFIKATION.md
└── README.md
```

Installation: HA → Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories → `https://github.com/Morbilus85/grow-tagebuch` → „Grow-Tagebuch“ installieren → in Seitenleiste anzeigen.

## 10. Offene Punkte

Geklärt: Port 2 = Lampe · Lichtplan Autos 20/4 · Kalibrierung per eigener Messung (Anleitung: `docs/LICHTMESSUNG.md`).

1. **Etikett-Dosierungen** für DiMikro, Rootmax, Ackerschachtelhalm-Konzentrat, Brennnesselpulver, Aloe-Vera-Puder, Neem Cake (Fotos folgen).


## Anhang A – Inventar zum Start

BioBizz: Root-Juice, CalMag, Bio-Heaven, Bio-Bloom, Bio-Grow, Top-Max, Acti-Vera, Bio-Down, Worm-Humus · DiMikro Bodenhilfsstoff · Neemöl · Ackerschachtelhalm-Konzentrat · Bio-Backmalz · Melasse · Rootmax · Brennnesselpulver · Neem Cake · Aloe-Vera-Puder.

## Anhang B – BioBizz-Schema All-Mix (ml/l, Microbes g/l)

Quelle: [BioBizz Nutrient Schedule](https://www.biobizz.com/wp-content/uploads/2021/10/Nutrient-Schedule-DE-Microbes-2021.pdf) (Stand 2021, identisch mit Ausgabe 2024). Fett = im Inventar vorhanden.

| Produkt | Anzucht | Wachstum | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 |
|---|---|---|---|---|---|---|---|---|---|---|
| **Root-Juice** | 4 | 4 | 2 | 2 | – | – | – | – | – | – |
| **Bio-Grow** | 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 1 |
| **Bio-Bloom** | – | – | 1 | 2 | 3 | 3 | 3 | 4 | 4 | 4 |
| **Top-Max** | – | – | 1 | 2 | 2 | 3 | 3 | 4 | 4 | 4 |
| **Bio-Heaven** | 2 | 2 | 2 | 3 | 4 | 5 | 5 | 4 | 4 | 3 |
| **Acti-Vera** | 2 | 2 | 3 | 4 | 5 | 5 | 3 | 3 | 2 | 1 |
| Microbes (g) | 0,4 | 0,4 | 0,2 | 0,2 | 0,4 | 0,4 | 0,4 | 0,2 | 0,2 | 0,2 |
| Fish-Mix | Alternative zu Bio-Grow, nicht beides | | | | | | | | | |

Danach Woche 9 nur Wasser, Woche 10 Ernte. Das Light-Mix-Schema (höhere Bio-Grow-Dosen in B2–B4, zusätzlich Alg-A-Mic) wird ebenfalls hinterlegt, für schwach gedüngte Erden.

## Anhang C – Wasserprofil Essen

Quelle: [Stadtwerke Essen, Quartalsanalyse Q4/2025, Verbundwasserwerk](https://www.stadtwerke-essen.de/fileadmin/user_upload/pdf/netz/2025-4._Quartal_00-0350_SWE.pdf)

| Parameter | Wert |
|---|---|
| Leitfähigkeit (25 °C) | 467 µS/cm (EC 0,47) |
| pH | 7,9 |
| Säurekapazität pH 4,3 | 2,08 mmol/l |
| Gesamthärte / Karbonathärte | 7,2 °dH / 5,8 °dH (weich) |
| Calcium / Magnesium | 39 / 7,6 mg/l |
| Kalium / Natrium | 4,4 / 39 mg/l |
| Chlorid / Sulfat / Nitrat | 52 / 38 / 10,8 mg/l |
