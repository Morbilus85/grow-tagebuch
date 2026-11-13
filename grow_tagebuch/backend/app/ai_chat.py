"""KI-Begutachtung und freie Fragen (Claude-API, Opus) mit Kontext aus der App.

Ablauf: Kilian startet einen Check (Pflanze, mit Fotos) oder eine Frage (Pflanze oder Zelt). Jede Antwort ist
strukturiertes JSON (Antworttext, Ampel, Befunde, nächste Schritte, Foto-Anforderungen, Vorschläge, Fazit).
Die KI ändert nie selbst etwas – Vorschläge übernimmt Kilian per Knopf.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from PIL import Image
from sqlmodel import Session, select

from . import services
from .db import PHOTO_DIR
from .models import (
    AiChat,
    AiMessage,
    ClimateSample,
    LogEntry,
    PestCase,
    Photo,
    Plant,
    Product,
    Run,
    Setup,
    SoilProfile,
    Strain,
    Task,
    WaterProfile,
    now,
)
from .strain_info import API_URL, _error, _headers, api_key

log = logging.getLogger("grow.ai")

MODEL = "claude-opus-5-5"
# USD pro Mio. Token (Opus 5.5, Stand 11/2026): Eingabe, Ausgabe, Cache schreiben, Cache lesen
PRICE = {"input": 4.0, "output": 20.0, "cache_write": 5.0, "cache_read": 0.20}
API_PX = 1568  # längste Kante fürs Modell (größer bringt keine Details, kostet nur Token)
MAX_AUTO_PHOTOS = 3
BUSY_TIMEOUT = timedelta(minutes=10)

AMPEL = {"unauffaellig": "Unauffällig", "beobachten": "Beobachten", "handeln": "Handeln"}

SYSTEM = """Du bist ein erfahrener Berater für organischen Cannabis-Homegrow (legal nach KCanG, Deutschland) und hilfst
Kilian in seinem Grow-Tagebuch. Er baut indoor im Zelt in Erde an, ausschließlich organisch (BioBizz und eigene Zusätze).
Antworte auf Deutsch, direkt, knapp und ehrlich – keine Beschönigung, aber auch keine Panik.

Arbeitsweise:
- Nutze den mitgelieferten Kontext (Phase, Logs, Klima, Erde, Wasser, Inventar, frühere Checks) aktiv. Oft erklärt er mehr
  als das Foto: z. B. Hellgrün im Sämlingsalter bei vorgedüngter Erde ist normal; sehr häufiges Gießen spricht für
  Überwässerung statt Mangel.
- Organisch zuerst Ursachen prüfen: Gießverhalten, pH, Klima/VPD, Licht. Erst dann Zusätze. Konservativ – bei
  vorgedüngter Erde ist Überdüngung am Anfang das größere Risiko als Mangel.
- Mängel, pH-Probleme, Überwässerung und Lichtstress sehen sich ähnlich. Nenne bei Befunden ehrlich die Sicherheit und
  was dagegen spricht. Wenn nichts auffällig ist, sag das klar – finde nicht auf Biegen und Brechen etwas.
- Fotos entstehen oft unter der Growlampe. Die Lampe (siehe Kontext) ist Vollspektrum-Weißlicht mit leichtem Farbstich.
  Ist ein weißes Blatt oder eine Graukarte im Bild, nutze sie als Weißreferenz. Beurteile Farbtöne vorsichtig.
- Reicht ein Bild nicht (zu weit weg, unscharf, Blattunterseite nötig, Farbstich zu stark), fordere gezielt ein Foto an
  (photo_requests: was genau, warum). Lieber nachfragen als raten.
- Dosierungen nur aus den Etikettangaben im Inventar oder allgemein anerkannten Herstellerangaben; erfinde keine. Ist
  eine Dosierung unbekannt, sag das. Bevorzuge Mittel, die Kilian laut Inventar vorrätig hat.
- Die App schaltet nichts in Home Assistant. Konkrete Dinge, die Kilian übernehmen könnte (Aufgabe anlegen, Notiz ins
  Tagebuch), gibst du als suggestions zurück – nur wenn sie wirklich sinnvoll sind, meist 0–2.
- Gießzeitpunkt: Es gibt keine Topfwaage. Schätze aus Abstand und Menge der letzten Gaben, Topfgröße, Phase, Pflanzengröße
  und Klima, und sag, woran Kilian es prüfen kann (Topf anheben, Fingerprobe 2–3 cm).

Antwortformat (JSON, alle Felder):
- reply: deine eigentliche Antwort an Kilian, gut lesbar, kurze Absätze, bei Bedarf Aufzählungen mit „- “.
- ampel: Gesamteindruck der Pflanze bzw. Lage (unauffaellig | beobachten | handeln) oder „keine“, wenn die Frage das
  nicht betrifft.
- findings: konkrete Befunde (leer, wenn nichts auffällt oder es eine reine Rückfrage ist).
- next_steps: konkrete nächste Schritte in sinnvoller Reihenfolge (kann leer sein).
- comparison: Vergleich zum letzten Check (besser/gleich/schlechter und woran), sonst leer.
- photo_requests: benötigte zusätzliche Fotos, sonst leer.
- suggestions: Vorschläge zum Übernehmen, sonst leer.
- summary: Fazit des gesamten bisherigen Gesprächs in 1–3 Sätzen (Zustand, Hauptbefund, vereinbarte Maßnahme). Dient
  beim nächsten Check als Vergleichsbasis."""

_S = {"type": "string"}
_I = {"type": "integer"}
SCHEMA = {
    "type": "object",
    "properties": {
        "reply": _S,
        "ampel": {"type": "string", "enum": ["unauffaellig", "beobachten", "handeln", "keine"]},
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "title": _S, "confidence": {"type": "string", "enum": ["hoch", "mittel", "niedrig"]},
            "evidence": {**_S, "description": "woran erkennbar"}, "against": {**_S, "description": "was dagegen spricht"}},
            "required": ["title", "confidence", "evidence", "against"], "additionalProperties": False}},
        "next_steps": {"type": "array", "items": _S},
        "comparison": _S,
        "photo_requests": {"type": "array", "items": {"type": "object", "properties": {"what": _S, "why": _S},
                                                     "required": ["what", "why"], "additionalProperties": False}},
        "suggestions": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["aufgabe", "notiz"]},
            "title": _S, "text": _S,
            "due_in_days": {**_I, "description": "Aufgabe fällig in x Tagen (0 = heute)"},
            "interval_days": {**_I, "description": "Wiederholung in Tagen, 0 = einmalig"}},
            "required": ["kind", "title", "text", "due_in_days", "interval_days"], "additionalProperties": False}},
        "summary": _S,
    },
    "additionalProperties": False,
}
SCHEMA["required"] = list(SCHEMA["properties"])


# ---------------------------------------------------------------- Kontext

def _f(v, nd=1) -> str:
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",")


def _log_line(l: LogEntry, names: dict) -> str:
    parts = [f"{l.ts:%d.%m. %H:%M}", l.type]
    if l.volume_l:
        parts.append(f"{_f(l.volume_l, 2)} l")
    if l.ph_in:
        parts.append(f"pH {_f(l.ph_in)}")
    if l.ec_in:
        parts.append(f"EC {_f(l.ec_in, 2)}")
    if l.ph_runoff or l.ec_runoff or l.runoff_l:
        parts.append(f"Runoff {_f(l.runoff_l, 2)} l pH {_f(l.ph_runoff)} EC {_f(l.ec_runoff, 2)}")
    if l.pot_weight_kg:
        parts.append(f"Topf {_f(l.pot_weight_kg, 2)} kg")
    if l.height_cm:
        parts.append(f"Höhe {_f(l.height_cm, 0)} cm")
    if l.lamp_distance_cm:
        parts.append(f"Lampe {_f(l.lamp_distance_cm, 0)} cm")
    if l.nodes:
        parts.append(f"{l.nodes} Nodien")
    if l.technique_key:
        parts.append(f"Training {l.technique_key}")
    if l.products:
        parts.append("Produkte: " + ", ".join(f"{p.get('name') or names.get(p.get('product_key'), p.get('product_key'))} "
                                             f"{_f(p.get('amount'), 2) if p.get('amount') is not None else ''}{p.get('unit') or ''}"
                                             f"{' (' + _f(p.get('per_l'), 2) + '/l)' if p.get('per_l') else ''}"
                                             for p in l.products))
    if l.severity:
        parts.append(f"Schwere {l.severity}")
    if l.text:
        parts.append(f"„{l.text[:300]}“")
    return " | ".join(parts)


def _climate(session: Session, setup_id: int, days: int = 7) -> str:
    since = datetime.now() - timedelta(days=days)
    rows = session.exec(select(ClimateSample).where(ClimateSample.setup_id == setup_id, ClimateSample.ts >= since)
                        .order_by(ClimateSample.ts)).all()
    if not rows:
        return "Keine Klimadaten aufgezeichnet."
    by_day: dict[date, list] = {}
    for r in rows:
        by_day.setdefault(r.ts.date(), []).append(r)
    out = ["Tag | Temp min/Ø/max °C | rLF min/Ø/max % | VPD Ø kPa | Lampe an (Anteil) | Heizung/Heizmatte an (Anteil)"]
    for d, rs in by_day.items():
        def stat(attr, lo=None, hi=None):
            vals = [getattr(r, attr) for r in rs if getattr(r, attr) is not None]
            los = [getattr(r, lo) for r in rs if lo and getattr(r, lo) is not None] or vals
            his = [getattr(r, hi) for r in rs if hi and getattr(r, hi) is not None] or vals
            return (min(los), sum(vals) / len(vals), max(his)) if vals else (None, None, None)
        t = stat("temp", "temp_min", "temp_max")
        h = stat("rh", "rh_min", "rh_max")
        v = stat("vpd")
        share = lambda attr: (f"{100 * sum(1 for r in rs if getattr(r, attr)) / len(rs):.0f} %"  # noqa: E731
                              if any(getattr(r, attr) is not None for r in rs) else "–")
        lamp = (f"{100 * sum(1 for r in rs if (r.light_level or 0) > 0) / len(rs):.0f} %"
                if any(r.light_level is not None for r in rs) else "–")
        out.append(f"{d:%d.%m.} | {_f(t[0])}/{_f(t[1])}/{_f(t[2])} | {_f(h[0], 0)}/{_f(h[1], 0)}/{_f(h[2], 0)} | "
                   f"{_f(v[1], 2)} | {lamp} | {share('heater_on')}/{share('heatmat_on')}")
    last = rows[-1]
    out.append(f"Letzter Messwert {last.ts:%d.%m. %H:%M}: {_f(last.temp)} °C, {_f(last.rh, 0)} % rLF, VPD {_f(last.vpd, 2)} kPa")
    return "\n".join(out)


def _inventory(session: Session) -> str:
    rows = session.exec(select(Product).where(Product.in_stock == True).order_by(Product.kind, Product.name)).all()  # noqa: E712
    lines = []
    for p in rows:
        dose = ""
        if p.label_dose_min or p.label_dose_max:
            dose = f", Etikett {_f(p.label_dose_min, 2)}–{_f(p.label_dose_max, 2)} {p.unit}/l"
        lines.append(f"- {p.name} ({p.brand or '–'}, {p.kind}, {', '.join(p.application or [])}{dose})"
                     + (f" – {p.notes[:120]}" if p.notes else ""))
    return "\n".join(lines) or "Kein Inventar erfasst."


def _strain_text(st: Optional[Strain]) -> str:
    if not st:
        return "Sorte unbekannt."
    i = st.info or {}
    bits = [f"{st.name} ({st.breeder or 'Breeder unbekannt'}, {'Autoflower' if st.auto else 'photoperiodisch'})"]
    for k, label in (("seed_to_harvest_text", "Samen bis Ernte"), ("height_text", "Höhe"), ("structure", "Wuchs"),
                     ("difficulty", "Schwierigkeit")):
        if i.get(k):
            bits.append(f"{label}: {i[k]}")
    if st.seed_to_harvest_days:
        bits.append(f"Laufzeit {st.seed_to_harvest_days} Tage")
    if i.get("specials"):
        bits.append("Besonderheiten: " + "; ".join(i["specials"][:4]))
    return "\n".join(bits)


def _run_text(session: Session, run: Run, setup: Optional[Setup]) -> str:
    soil = session.get(SoilProfile, run.soil_id) if run.soil_id else None
    water = session.get(WaterProfile, run.water_id) if run.water_id else None
    lines = [f"Durchgang „{run.name}“, Start {run.start_date:%d.%m.%Y}, Lichtplan {_f(run.light_hours, 0)} h ab {run.light_on_time}, "
             f"Lampenstufe {run.light_level or '–'}, Lampe–Spitze {run.lamp_distance_cm or '–'} cm"]
    if setup:
        lines.append(f"Zelt „{setup.name}“ {setup.width_cm or '?'}×{setup.depth_cm or '?'}×{setup.height_cm or '?'} cm, "
                     f"Medium {setup.medium}, Lampe {setup.lamp or 'Ionframe EVO4 (Vollspektrum-LED, Stufen 1–10)'}")
    if soil:
        comps = ", ".join(f"{c.get('name')} {c.get('pct')} %" for c in (soil.components or []) if c.get("name"))
        lines.append(f"Erde: {soil.name} ({soil.schedule_type}, vorgedüngt ca. {soil.prefertilized_weeks} Wochen, "
                     f"Wurmhumus {soil.worm_humus_pct} %){': ' + comps if comps else ''}")
    if water:
        lines.append(f"Wasser: {water.name}, EC {_f(water.ec, 2)} mS/cm, pH {_f(water.ph)}, Ca {_f(water.ca_mg_l, 0)} mg/l, "
                     f"Mg {_f(water.mg_mg_l, 0)} mg/l, Härte {_f(water.hardness_dh)} °dH")
    return "\n".join(lines)


def _cases_text(session: Session, run_id: int, plant_id: Optional[int]) -> str:
    cs = services.open_cases(session, run_id, plant_id)
    if not cs:
        return "Keine offenen Schädlingsfälle."
    return "\n".join(f"- {c['name']} ({'ganzes Zelt' if c['scope'] == 'zelt' else 'einzelne Pflanzen'}), {c['status']}, "
                     f"Schwere {c['severity']}, seit {c['started_on']}" for c in cs)


def _plant_block(session: Session, plant: Plant, run: Run, setup: Optional[Setup], detail: bool) -> str:
    today = date.today()
    st = session.get(Strain, plant.strain_id) if plant.strain_id else None
    status = services.plant_status(session, plant, run, setup, today)
    ph = status["phase"]
    names = {p.key: p.name for p in session.exec(select(Product)).all()}
    lines = [f"Pflanze „{plant.name}“ (Status {plant.status}), Topf {_f(plant.pot_l, 0)} l",
             f"Phase: {ph['label']}, Tag {ph['day'] or '–'} seit Auflaufen, Woche {ph['week'] or '–'}"
             + (f", Blütewoche {ph['bloom_week']}" if ph.get("bloom_week") else "")
             + (f", voraussichtliche Ernte {ph['harvest_date']} (in {ph['days_to_harvest']} Tagen)" if ph.get("harvest_date") else ""),
             "Daten: " + ", ".join(f"{label} {getattr(plant, k):%d.%m.%Y}" for k, label in
                                   (("soaked_on", "eingeweicht"), ("planted_on", "gesetzt"), ("sprouted_on", "aufgelaufen"),
                                    ("preflower_on", "Vorblüte bestätigt"), ("flip_on", "12/12 ab")) if getattr(plant, k)),
             f"Düngefaktor {_f(plant.feed_factor, 2)}" + (", Mg-Mangel markiert" if plant.mg_deficiency_flag else ""),
             "Sorte: " + _strain_text(st)]
    if plant.notes:
        lines.append(f"Notizen: {plant.notes[:400]}")
    if status["space"].get("messages"):
        lines.append("Platz: " + " ".join(status["space"]["messages"]))
    if status["actions"]:
        lines.append("Hinweise der App: " + " ".join(status["actions"]))
    days = 21 if detail else 10
    logs = session.exec(select(LogEntry).where(LogEntry.plant_id == plant.id,
                                               LogEntry.ts >= datetime.now() - timedelta(days=days),
                                               LogEntry.type != "ai_check")
                        .order_by(LogEntry.ts)).all()
    lines.append(f"Tagebuch der letzten {days} Tage ({len(logs)} Einträge):")
    lines += [f"  {_log_line(l, names)}" for l in logs] or ["  (keine)"]
    waters = session.exec(select(LogEntry).where(LogEntry.plant_id == plant.id, LogEntry.type.in_(("watering", "feeding")))
                          .order_by(LogEntry.ts.desc())).all()
    if waters:
        w = waters[0]
        lines.append(f"Letztes Gießen: {w.ts:%d.%m. %H:%M} ({(datetime.now() - w.ts).total_seconds() / 86400:.1f} Tage her), "
                     f"{_f(w.volume_l, 2)} l. Gaben insgesamt: {len(waters)}.")
    return "\n".join(lines)


def _previous_checks(session: Session, plant_id: int, exclude: Optional[int]) -> list[AiChat]:
    q = select(AiChat).where(AiChat.plant_id == plant_id, AiChat.kind == "check", AiChat.summary != "")
    if exclude:
        q = q.where(AiChat.id != exclude)
    return list(session.exec(q.order_by(AiChat.created_at.desc()).limit(3)).all())


def build_context(session: Session, chat: AiChat) -> str:
    parts = [f"Heute ist {datetime.now():%A, %d.%m.%Y, %H:%M} Uhr."]
    if chat.plant_id:
        plant = session.get(Plant, chat.plant_id)
        run = session.get(Run, plant.run_id)
        setup = session.get(Setup, run.setup_id)
        parts += ["## Pflanze", _plant_block(session, plant, run, setup, detail=True),
                  "## Durchgang und Zelt", _run_text(session, run, setup)]
        others = session.exec(select(Plant).where(Plant.run_id == run.id, Plant.status == "aktiv", Plant.id != plant.id)).all()
        if others:
            parts.append("Weitere aktive Pflanzen im Zelt: " + ", ".join(
                f"{o.name} ({services.phase_of(session, o).label})" for o in others))
        parts += ["## Klima im Zelt (letzte 7 Tage)", _climate(session, run.setup_id),
                  "## Schädlinge", _cases_text(session, run.id, plant.id)]
        prev = _previous_checks(session, plant.id, chat.id)
        if prev:
            parts.append("## Frühere KI-Checks dieser Pflanze")
            parts += [f"- {c.created_at:%d.%m.%Y}: Ampel {AMPEL.get(c.ampel, c.ampel or '–')}. {c.summary}" for c in prev]
    else:
        setup = session.get(Setup, chat.setup_id)
        runs = session.exec(select(Run).where(Run.setup_id == setup.id, Run.status == "aktiv")).all()
        parts.append("## Zelt")
        parts.append(f"„{setup.name}“, Status {setup.status}, Medium {setup.medium}")
        for run in runs:
            parts += [f"## Durchgang {run.name}", _run_text(session, run, setup)]
            for p in session.exec(select(Plant).where(Plant.run_id == run.id, Plant.status == "aktiv")).all():
                parts.append(_plant_block(session, p, run, setup, detail=False))
            parts += ["### Schädlinge", _cases_text(session, run.id, None)]
            tasks = services.tasks_due(session, run.id)
            if tasks:
                parts.append("Fällige Aufgaben: " + ", ".join(t.title for t in tasks))
        parts += ["## Klima (letzte 7 Tage)", _climate(session, setup.id)]
    parts += ["## Inventar (vorrätig)", _inventory(session)]
    return "\n\n".join(parts)


# ---------------------------------------------------------------- Bilder

def _image_block(session: Session, photo_id: int) -> Optional[list]:
    p = session.get(Photo, photo_id)
    if not p or not (PHOTO_DIR / p.filename).exists():
        return None
    img = Image.open(PHOTO_DIR / p.filename)
    img.thumbnail((API_PX, API_PX))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    entry = session.get(LogEntry, p.log_id)
    label = f"Foto {photo_id} vom {p.taken_at:%d.%m.%Y %H:%M}" + (f" (Eintrag: {entry.text[:120]})" if entry and entry.text else "")
    return [{"type": "text", "text": label},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.b64encode(buf.getvalue()).decode()}}]


def latest_photos(session: Session, plant_id: int, limit: int = MAX_AUTO_PHOTOS, days: int = 7) -> list[int]:
    """Neueste Fotos der Pflanze (max. `days` alt, ohne Fotos aus früheren Checks doppelt zu werten)."""
    since = datetime.now() - timedelta(days=days)
    rows = session.exec(select(Photo).join(LogEntry, LogEntry.id == Photo.log_id)
                        .where(LogEntry.plant_id == plant_id, Photo.taken_at >= since)
                        .order_by(Photo.taken_at.desc()).limit(limit)).all()
    return [p.id for p in rows]


# ---------------------------------------------------------------- Gespräch

def _user_content(session: Session, msg: AiMessage) -> list:
    content: list = []
    for pid in msg.photo_ids or []:
        content += _image_block(session, pid) or [{"type": "text", "text": f"(Foto {pid} nicht mehr vorhanden)"}]
    content.append({"type": "text", "text": msg.text or "(keine weitere Frage)"})
    return content


def build_messages(session: Session, chat: AiChat, msgs: list[AiMessage]) -> list[dict]:
    first_user = next(m for m in msgs if m.role == "user")
    intro = chat.context.get("text") or build_context(session, chat)
    task = ("Begutachte die Pflanze anhand der Fotos und des Kontexts." if chat.kind == "check"
            else "Kilian hat eine Frage. Beantworte sie mit Blick auf den Kontext.")
    head: list = [{"type": "text", "text": f"# Kontext aus dem Grow-Tagebuch\n\n{intro}"}]
    prev_photo = chat.context.get("previous_photo_id")
    if prev_photo:
        block = _image_block(session, prev_photo)
        if block:
            block[0]["text"] = "Zum Vergleich: Foto vom letzten Check – " + block[0]["text"]
            head += block
    if chat.kind == "check" and not first_user.photo_ids:
        head.append({"type": "text", "text": "Hinweis: Für diese Pflanze gibt es keine aktuellen Fotos. Fordere die "
                                              "nötigen Fotos an."})
    head.append({"type": "text", "text": f"# Aufgabe\n{task}"})
    out: list[dict] = []
    for m in msgs:
        if m.role == "user":
            content = _user_content(session, m)
            if m is first_user:
                content = head + content
            out.append({"role": "user", "content": content})
        else:
            out.append({"role": "assistant", "content": [{"type": "text", "text": json.dumps(m.data, ensure_ascii=False)}]})
    out[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}  # Verlauf + Fotos für Rückfragen cachen
    return out


def cost(usage: dict) -> float:
    return round((usage.get("input_tokens", 0) * PRICE["input"] + usage.get("output_tokens", 0) * PRICE["output"]
                  + usage.get("cache_creation_input_tokens", 0) * PRICE["cache_write"]
                  + usage.get("cache_read_input_tokens", 0) * PRICE["cache_read"]) / 1e6, 4)


async def ask(messages: list[dict]) -> tuple[dict, dict]:
    key = api_key()
    if not key:
        raise RuntimeError("Kein Claude-API-Schlüssel hinterlegt (Add-on → Konfiguration → anthropic_api_key).")
    body = {"model": MODEL, "max_tokens": 8000, "system": SYSTEM, "messages": messages,
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}}}
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(API_URL, headers=_headers(key), json=body)
    if r.status_code != 200:
        raise RuntimeError(_error(r))
    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("Antwort der KI war nicht lesbar – bitte noch einmal senden.")
    return out, data.get("usage", {})


def _sync_log(session: Session, chat: AiChat) -> None:
    """Checks erscheinen als Eintrag im Zeitstrahl der Pflanze (Text = Fazit)."""
    if chat.kind != "check" or not chat.plant_id:
        return
    text = f"{AMPEL.get(chat.ampel, '–')}. {chat.summary}".strip()
    entry = session.get(LogEntry, chat.log_id) if chat.log_id else None
    if not entry:
        plant = session.get(Plant, chat.plant_id)
        entry = LogEntry(plant_id=plant.id, run_id=plant.run_id, ts=chat.created_at, type="ai_check")
    entry.text = text
    entry.tags = [f"ai_chat:{chat.id}"]
    session.add(entry)
    session.flush()
    chat.log_id = entry.id


async def answer(chat_id: int) -> None:
    """Antwort auf die letzte Nachricht holen und speichern (läuft im Hintergrund)."""
    from .db import engine
    with Session(engine) as session:
        chat = session.get(AiChat, chat_id)
        msgs = list(session.exec(select(AiMessage).where(AiMessage.chat_id == chat_id).order_by(AiMessage.id)).all())
        messages = build_messages(session, chat, msgs)
    try:
        out, usage = await ask(messages)
    except Exception as e:  # noqa: BLE001
        log.exception("KI-Antwort für Gespräch %s fehlgeschlagen", chat_id)
        with Session(engine) as session:
            chat = session.get(AiChat, chat_id)
            chat.busy, chat.error = False, str(e)[:400]
            session.add(chat)
            session.commit()
        return
    with Session(engine) as session:
        chat = session.get(AiChat, chat_id)
        c = cost(usage)
        session.add(AiMessage(chat_id=chat_id, role="assistant", text=out.get("reply", ""), data=out,
                              usage={**usage, "cost_usd": c}))
        if out.get("ampel") in AMPEL:
            chat.ampel = out["ampel"]
        if out.get("summary"):
            chat.summary = out["summary"]
        chat.cost_usd = round((chat.cost_usd or 0) + c, 4)
        chat.busy, chat.error, chat.updated_at = False, "", now()
        _sync_log(session, chat)
        session.add(chat)
        session.commit()
    log.info("KI-Antwort für Gespräch %s gespeichert (%.3f USD)", chat_id, c)


def release_stale(session: Session, chat: AiChat) -> None:
    """Nach einem Neustart hängengebliebenes „busy“ lösen."""
    if chat.busy and now() - chat.updated_at > BUSY_TIMEOUT:
        chat.busy, chat.error = False, "Keine Antwort erhalten (Add-on neu gestartet?) – bitte noch einmal senden."
        session.add(chat)
        session.commit()


def apply_suggestion(session: Session, chat: AiChat, msg: AiMessage, index: int) -> dict:
    sugg = (msg.data.get("suggestions") or [])[index]
    if sugg.get("applied"):
        return sugg
    run_id = session.get(Plant, chat.plant_id).run_id if chat.plant_id else chat.run_id
    if sugg["kind"] == "aufgabe":
        t = Task(run_id=run_id, title=sugg["title"][:120], notes=sugg.get("text", ""),
                 due_on=date.today() + timedelta(days=max(0, sugg.get("due_in_days") or 0)),
                 interval_days=sugg.get("interval_days") or None)
        session.add(t)
        session.flush()
        ref = {"task_id": t.id}
    else:
        if not run_id:
            raise ValueError("Kein aktiver Durchgang für die Notiz")
        l = LogEntry(run_id=run_id, plant_id=chat.plant_id, type="note",
                     text=f"{sugg['title']}: {sugg.get('text', '')}".strip(": "), tags=[f"ai_chat:{chat.id}"])
        session.add(l)
        session.flush()
        ref = {"log_id": l.id}
    data = dict(msg.data)
    items = list(data.get("suggestions") or [])
    items[index] = {**items[index], "applied": True, **ref}
    data["suggestions"] = items
    msg.data = data
    session.add(msg)
    session.commit()
    return items[index]
