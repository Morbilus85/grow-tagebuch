# Grow-Tagebuch

Öffne die App über die Seitenleiste von Home Assistant. Beim ersten Start legt sie dein Zelt, die Erde,
das Essener Leitungswasser, dein Inventar, das BioBizz-Schema und die Lichtkalibrierung an.

## Einstellungen

- **anthropic_api_key**: wird erst für die KI-Funktionen (Phase 2) gebraucht.
- **ntfy_server / ntfy_topic**: für Push-Erinnerungen (folgt in Phase 1b).
- **climate_interval_minutes**: wie oft Temperatur und Feuchte aus Home Assistant gespeichert werden.

## Daten

Datenbank und Fotos liegen im Add-on-Ordner und sind Teil der Home-Assistant-Backups.
Die App liest Sensoren nur, sie schaltet nichts in Home Assistant.
