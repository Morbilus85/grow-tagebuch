## 0.7.10

- Sorten-Recherche: Antwortlimit der Websuche auf 16 000 Token erhöht – bei vielen Einzelquellen war es vorher aufgebraucht,
  bevor Text kam.

## 0.7.9

- Sorten-Recherche: leere Websuche (kommt sporadisch vor) wird einmal automatisch wiederholt.

## 0.7.8

- Sortenwerte: Hersteller-Seite (Breeder, Shops, Datenbanken – oft abgeschriebenes Datenblatt) und Grower-Seite werden
  getrennt gemittelt, dann 50/50. Kopien des Datenblatts drücken den Wert nicht mehr Richtung Breeder.
- Recherche fragt Endhöhen je Quelle gezielt ab. Steckbrief zeigt beide Seiten-Durchschnitte.

## 0.7.7

- Sorten neu recherchieren: läuft jetzt zu Ende und wird gespeichert, auch wenn HA die Verbindung nach 30 s trennt.
  Fehler landen im Add-on-Log.

## 0.7.6

- Sorten-Recherche: Dauer und Höhe werden je Quelle einzeln erfasst (Breeder, Shop, Datenbank, Grower/Forum, mit Kontext).
  Die App bildet daraus selbst den Mittelwert (Mitte je Spanne, alle Quellen gleich gewichtet) und rechnet damit.
- Steckbrief: neuer Abschnitt „wer sagt was“ mit allen Angaben und dem Mittelwert.

## 0.7.5

- Sorten-Recherche: realistische Werte = Mitte der üblichen Grower-Spanne, Ausreißer werden ignoriert (vorher oberes Ende,
  dadurch z. B. 90 statt ca. 77 Tage).

## 0.7.4

- Sorten-Recherche: Die App rechnet jetzt mit realistischen Werten aus Grower-Berichten (Dauer, Endhöhe) statt mit den
  Breeder-Bestwerten. Die Breeder-Angaben bleiben im Steckbrief sichtbar.
- Steckbrief zeigt neu „App rechnet mit“ – die Werte für Phasen, Erntefenster und Platzberechnung.
- Bestehende Sorten: „Infos aus dem Internet holen“ einmal neu ausführen, damit die realistischen Werte übernommen werden.

## 0.7.3

- Sorten-Recherche: Auslesen über „Structured Outputs“ der Claude-API statt erzwungenem Tool (das aktuelle Modell unterstützt kein erzwungenes Tool).

## 0.7.2

- Sorten-Recherche robuster: erst Websuche, dann Auslesen über ein festes Schema – kein „nicht lesbarer Steckbrief“ mehr durch Anführungszeichen im Text.

## 0.7.1

- Claude-API: Anmeldung nach aktuellem Verfahren (Bearer-Token), verständliche Fehlermeldungen (ungültiger Schlüssel, kein Guthaben, Workspace).
- Sortenseite: Button „API-Schlüssel testen“.

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
