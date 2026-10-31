## 0.7.0

- Sorten-Steckbrief (Mehr → Sorten): Typ, Genetik, THC/CBD, Samen bis Ernte (Breeder und Erfahrungswerte), Höhe, Ertrag, Schwierigkeit, Wuchs, Aroma, Wirkung, Besonderheiten, Anbautipps, Quellen.
- Training je Sorte: jede Technik bewertet (besonders geeignet / geeignet / mit Vorsicht / ungeeignet) mit Begründung, verlinkt zur Anleitung. Ohne Steckbrief gilt die allgemeine Eignung für Autos bzw. Photos; passt die Sorte nicht ins Zelt, wird LST hochgestuft.
- „Infos aus dem Internet holen“: recherchiert die Sorte über die Claude-API mit Websuche (Herstellerseite, Grower-Erfahrungen) und füllt Steckbrief und Eckdaten aus – beim Anlegen einer neuen Sorte und auf der Sortenseite. Braucht den Claude-API-Schlüssel in der Add-on-Konfiguration.
- Kurz-Steckbrief auf der Pflanzenseite und beim Samen eintragen.

## 0.6.2

- Durchgang löschen (Durchgangsseite, neben Speichern) für Fehleingaben: entfernt Pflanzen, Einträge und Fotos; offene Aufgaben und Schädlingsfälle wandern in den aktuellen Durchgang.
- Samen eintragen: Eine neu eingetippte Sorte wird beim Eintragen automatisch mitgespeichert, auch ohne vorher „Sorte speichern“ zu drücken.

## 0.6.1

- Neustart in zwei Schritten: Beim Abbrechen nur Grund und „Direkt neu starten“, danach öffnet sich die eigene Seite „Samen eintragen“ (Sorte und Anzahl, auch mehrere Sorten, Keimmethode, Einweich-Zeitpunkt, Topf).
- Durchgangsname wird automatisch erzeugt („Sorte – Saison Jahr“, bei Dopplung mit Nummer) und passt sich der gewählten Sorte an, bis du ihn von Hand änderst.
- „Neuer Durchgang“ unter Mehr: Name optional, führt direkt zu „Samen eintragen“. Auf der Durchgangsseite gibt es dafür zusätzlich den Button „Samen eintragen“.

## 0.6.0

- Pflanze abbrechen (Pflanzenseite → Daten bearbeiten → „Pflanze abbrechen“): mit Grund, Tagebuch und Fotos bleiben erhalten, die Pflanze verschwindet aus „Heute“ und zählt nicht mehr zum KCanG-Limit. „Wieder aktivieren“ macht das rückgängig.
- Durchgang abbrechen (Mehr → Durchgang → ganz unten): beendet alle aktiven Pflanzen. Optional direkt neu starten: übernimmt Zelt, Erde, Wasser, Düngeschema und Licht, legt die neuen Samen mit Keimmethode und Einweich-Zeitpunkt an; offene Aufgaben und zeltweite Schädlingsfälle laufen weiter.

## 0.5.3

- Heute: Ein-Klick-Button für den nächsten Meilenstein jeder Pflanze (Gesetzt, Aufgelaufen, Vorblüte) – übernimmt das heutige Datum und verschwindet danach.
- Datum wird in lokaler Zeit gesetzt (vorher kurz nach Mitternacht ggf. noch der Vortag).

## 0.5.2

- Heute: Pflanzen-Kacheln nebeneinander auf breiten Bildschirmen (Tablet, PC), untereinander auf dem Handy.

## 0.5.1

- Kleine Wassermengen werden in ml angezeigt statt auf 0 l gerundet.

## 0.5.0

- Schädlinge & Krankheiten: Befälle als Fälle mit Geltungsbereich (ganzes Zelt oder einzelne Pflanzen), Status, Befunden mit Fotos und Maßnahmen.
- Katalog mit 8 typischen Problemen und organischen Gegenmaßnahmen, gesperrt je nach Phase; Folgeanwendungen als Aufgaben.
- Offene Befälle als Hinweis auf „Heute“ und auf den betroffenen Pflanzen.

## 0.4.2

- Fotos werden vor dem Hochladen verkleinert; HEIC wird unterstützt; Fehler beim Foto-Upload werden angezeigt, der Eintrag bleibt erhalten.
- Kleine Mengen (z. B. 0,035 l) lassen sich überall eintragen.
- Heute: letzter Tagebucheintrag pro Pflanze.

## 0.4.1

- Living Soil: Anbauweise wählen (vegan oder vegan und tierisch).
- Tierische Zutaten: Knochenmehl, Krabbenschalenmehl, Fledermausguano, Hornspäne, Fischmehl, Blutmehl, Hühnermist.
- Neues Rezept „Klassisch selbst gemischt (Coots Mix)“, Top-Dress Blüte mit Guano und Knochenmehl.

## 0.4.0

- Living Soil: veganer Zutatenkatalog mit Inventar, Rezepte (vegan selbst gemischt, Monster Bud Mix, Plant BoOom, Aufbereitung) mit Mengenrechner und Einkaufsliste.
- Ansätze mit Reifezeit und Aufgaben (Feuchte prüfen, wenden), Übernahme als Erdprofil.
- Düngelogik „Living Soil“: keine Grunddünger, Tees und Top-Dress nach Phase und Intervall im Gieß-Assistenten.

## 0.3.0

- Keimung: 6 Methoden (Wasser + H2O2, Wasserglas, Küchenpapier, Direkt in die Erde, Anzuchtwürfel, Anritzen) mit Anleitung, Zeitplan und H2O2-Mischrechner.
- Pro Pflanze: Keimmethode, Start des Einweichens, nächster Schritt mit Zeitangabe; Einweichen für alle Pflanzen eines Durchgangs starten.

## 0.2.1

- Haushalt & KCanG: Erwachsene im Haushalt, Pflanzenlimit (3 pro Person), Warnung beim Überschreiten, Lagergrenze.
- SOG-Beschreibung an mehrere Erwachsene angepasst.

## 0.2.0

- Trainingsdatenbank: 11 Techniken (LST, Blätter wegstecken, Toppen, FIM, Mainlining, Supercropping, SCROG, SOG, Lollipopping, Entlauben, Schwazzing) mit Anleitung, Eignung für Autos/Photos, Zeitfenster und Erholungszeiten.
- Pro Pflanze: welche Technik jetzt passt, Warnung bei gestapeltem Stress.
- Nodien als Messwert; eigene Techniken und Notizen.

## 0.1.3

- Hochbeet-Setup entfernt; Setups lassen sich löschen.

## 0.1.2

- Licht: Stufe live vom Controller, Anzeige „aus“ bei ausgeschalteter Lampe, Hinweis dass PPFD berechnet ist.

## 0.1.1

- Sensoren aus Home Assistant werden jetzt gelesen (Umgebung im Startskript).
- Zeitzone aus Home Assistant statt UTC.

## 0.1.0

- Erste Version (Phase 1a): Heute-Ansicht, Pflanzen, Tagebuch mit Fotos, Gieß- und Düngeassistent,
  Klima aus Home Assistant, Licht/DLI aus Kalibrierung, Aufgaben, Inventar.
