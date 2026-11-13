## 0.12.0

- KI-Begutachtung: an der Pflanze „Begutachten“ – die neuesten Fotos (max. 4, frei wählbar oder neu aufnehmen) gehen mit
  Kontext an Claude Opus: Phase, Tagebuch der letzten 21 Tage (Gießen, pH/EC, Höhe, Training), Klima der letzten 7 Tage,
  Erde, Wasser, Lampe, Schädlingsfälle, Inventar, Fazit und Foto des letzten Checks.
- Antwort strukturiert: Ampel (unauffällig/beobachten/handeln), Befunde mit Sicherheit und Gegenargument, nächste Schritte,
  Vergleich zum letzten Check, Foto-Anforderungen (mit Foto-Knopf) und Vorschläge (Aufgabe/Notiz per „Übernehmen“).
- Danach als Chat weiter: Rückfragen, Fotos anhängen. Fotos landen zusätzlich im Tagebuch.
- „Frage stellen“ an der Pflanze und „KI fragen“ unter Klima (zeltweit), z. B. wann gießen.
- Jeder Check erscheint als Eintrag „KI-Check“ im Zeitstrahl, Kosten je Antwort und Gespräch werden angezeigt.
- Die KI ändert nie selbst etwas; Antworten laufen im Hintergrund (kein Abbruch durch HA-Ingress).

## 0.11.1

- Fotos im Eintrag: Auswahl wieder einzeln statt Mehrfachauswahl – die HA-App auf Android gab bei Mehrfachauswahl aus der
  Galerie eine leere Liste zurück, der Eintrag wurde ohne Foto gespeichert. Mehrere Fotos: einfach nacheinander „Weiteres Foto“.
- Gewählte Fotos erscheinen sofort als Vorschau (Antippen entfernt); kommt kein Foto an, gibt es einen Hinweis.
- Log-Zeile „Foto … gespeichert“ bzw. Warnung bei leerem Upload.

## 0.11.0

- Mehrere Zelte: neue Seite Mehr → Zelte (anlegen, Maße, Lampe, Medium Erde/RDWC, Status geplant/in Betrieb/abgebaut,
  Sensoren je Zelt – die Sensoren sind aus den Einstellungen hierher umgezogen).
- Heute: Zeltname über jedem Durchgang, unten „+ Weiterer Durchgang“. Beim Anlegen wird das freie Zelt vorausgewählt.
- Klima und Licht: Umschalter zwischen den Zelten; Klimaleiste unter „Heute“ öffnet direkt das richtige Zelt.
  Ohne eigene Lichtmessung rechnet ein Zelt kein PPFD (keine Fremdwerte der Ionframe).
- Inventar: eigene Produkte hinzufügen (Name, Marke, Art inkl. Mineraldünger/Hydro-Zusatz, Einheit, Dosis, vorhanden
  oder nicht – dann als Einkaufsliste unter „Nicht vorhanden“), bearbeiten und löschen. Vorgegebene Produkte bleiben.
- RDWC ist am Zelt vormerkbar; Reservoir-Protokoll, Zielwerte und Mineral-Düngeplan folgen, wenn System und Dünger feststehen.

## 0.10.0

- „Mehr“ aufgeräumt: nur noch Kacheln in Gruppen (Grow · Erde, Wasser & Dünger · Wissen · App), jede mit eigener Seite
  und Kurzinfo (aktiver Durchgang, fällige Aufgaben, Push an/aus). Neue Seiten Durchgänge, Sorten, Aufgaben,
  Erde & Wasser, Einstellungen (Push, Haushalt & KCanG, Sensoren, Export – aufklappbar). Reiter „Mehr“ bleibt auf
  allen Unterseiten markiert.
- Erde & Wasser: Wasserwerte per Knopf aus dem Internet (Ort/Stadtteil → Trinkwasseranalyse des Versorgers: EC, pH,
  Ca, Mg, Na, K, Cl, Sulfat, Nitrat, Härte, Säurekapazität, Versorger/Gebiet, Hinweise, Quellen). Alle Werte editierbar.
- Erde-Steckbrief per Knopf (Produktname → Herstellerangaben: Zusammensetzung, enthaltene Dünger, N/P₂O₅/K₂O/Mg,
  Salz, pH, Vorratsdüngung, Hinweise zur Abstimmung mit BioBizz). Weicht die Herstellerangabe von den Düngeplan-
  Einstellungen ab, lassen sie sich mit „Übernehmen“ setzen – nie automatisch. „Neue Erde“ anlegen mit Recherche.

## 0.9.0

- Push-Benachrichtigungen über ntfy (Mehr → Push-Benachrichtigungen):
  - Fällige Aufgaben einmal täglich zur eingestellten Uhrzeit (Standard 08:00, wird nach einem Neustart nachgeholt).
  - Klima-Alarm, wenn Temperatur oder Blatt-VPD länger als 30 min deutlich außerhalb des Zielbereichs der Phase liegen;
    Wiederholung frühestens nach 3 h, Entwarnung wenn wieder im Bereich. Optional „streng“ (jede Abweichung).
  - Warnung, wenn der Klimasensor 30 min keine Werte liefert.
  - Test-Push und „Aufgaben jetzt senden“. Topic/Server in der App, sonst aus der Add-on-Konfiguration.
- Mehr-Seite: Ladefehler in der Sensor-Liste behoben.

## 0.8.0

- Sorten-Steckbrief: nur noch offizielle Breeder-Angaben (Seedfinder nur als Ersatz, wenn der Breeder etwas nicht angibt).
  Keine Foren-/Diary-Werte, kein Mitteln, keine Nachrecherche – Recherche deutlich schneller, Steckbrief übersichtlich.
- Kurzfassung auf der Pflanzenseite zeigt jetzt auch die Wirkung.

## 0.7.11

- Sorten-Recherche: Fehlen Kernangaben (Wirkung, Aroma, Terpene, Ertrag, Schwierigkeit, Wuchs, THC, Genetik),
  wird gezielt nachrecherchiert und nur die Lücken werden gefüllt.

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
