# Lichtmessung – Kalibrierung Ionframe EVO4

Ziel: herausfinden, wie viel Licht (PPFD) bei welcher Stufe und welchem Abstand an der Pflanze ankommt. Danach rechnet die App Abstand und Stufe für jede Phase selbst aus.

Aufwand: ca. 20–30 Minuten, 17 Messwerte.

## Vorbereitung

1. Zelt schließen, Raumlicht aus, Fenster abdunkeln. Fremdlicht verfälscht die Messung.
2. Lampe 15 Minuten auf Stufe 10 vorwärmen. LEDs verlieren warm etwas Leistung.
3. Töpfe raus oder zur Seite. Gemessen wird auf einem flachen Untergrund (Karton, Kiste, Hocker), der auf die jeweilige Höhe gestellt wird.
4. Messgerät **waagerecht, Sensor nach oben**. Hand und Kopf nicht über den Sensor halten. Bei Handy-Apps die Kamera bzw. Diffusor nach oben.
5. Notieren, welches Gerät du nutzt: **PAR-Meter** (zeigt µmol/m²/s) oder **Lux-Meter** (zeigt lx). Beides ist ok, die App rechnet Lux um.

**Abstand** = von der Unterkante der Lampe bis zum Sensor. Später entspricht das dem Abstand Lampe → Spitze der Pflanze.

## Messpunkte im Zelt (90 × 90 cm)

```
 ┌───────────────────────┐
 │  E                 B  │   B, C, D, E: jeweils ca. 20 cm von beiden
 │                       │   Zeltwänden entfernt (nicht in die Ecke)
 │           A           │   A: genau Mitte
 │                       │
 │  D                 C  │
 └───────────────────────┘
```

Die Ecken direkt an der Wand brauchst du nicht. Dort steht ohnehin kaum eine Pflanze, und die Mylar-Wände verfälschen den Wert.

## Teil 1 – Mitte, verschiedene Stufen und Abstände (12 Werte)

Nur Punkt A. Stufe am Controller einstellen, 1 Minute warten, ablesen.

| Abstand | Stufe 3 | Stufe 5 | Stufe 7 | Stufe 10 |
|---|---|---|---|---|
| 30 cm | | | | |
| 45 cm | | | | |
| 60 cm | | | | |

Tipp: Lampe in der Höhe lassen und nur den Untergrund unter dem Sensor wechseln. Bei Abstand 30 cm auf Stufe 10 kann der Wert sehr hoch werden – das ist nur Messung, kein Problem.

## Teil 2 – Verteilung (5 Werte)

Einmal bei **45 cm, Stufe 7** alle fünf Punkte A–E messen.

| A | B | C | D | E |
|---|---|---|---|---|
| | | | | |

Daraus erkennt die App, wie stark das Licht zum Rand hin abfällt und ob die Pflanzen eher mittig stehen sollten.

## Optional – Stromverbrauch pro Stufe

AC Infinity veröffentlicht nicht, wie viel Prozent Leistung eine Stufe bedeutet. Die Stufen sind bei vielen Herstellern **nicht linear** (Stufe 1 ist meist mehr als 10 %). Teil 1 klärt das für die Praxis ohnehin, weil wir direkt das Licht messen.

Wenn du es genau wissen willst: Lampe über eine freie Zigbee-Steckdose mit Leistungsmessung anschließen und für jede Stufe 1–10 die Watt notieren.

## Danach

Werte hier im Chat schicken oder später direkt in der App eintragen. Die App erzeugt daraus eine Tabelle „Stufe × Abstand → PPFD“ und schlägt für jede Phase eine Kombination vor.
