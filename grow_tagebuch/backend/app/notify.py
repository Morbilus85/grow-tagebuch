"""Push-Benachrichtigungen über ntfy: tägliche Aufgabenliste und Klima-Alarm.

Einstellungen liegen in Setting "notify"; Server/Topic fallen auf die Add-on-Optionen zurück.
Die App liest HA weiterhin nur – ntfy ist ein externer Dienst, kein HA-Aufruf.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from sqlmodel import Session, select

from .db import DATA_DIR
from .logic import climate
from .models import ClimateSample, Plant, Run, Setting
from . import services

log = logging.getLogger("grow.notify")

DEFAULTS = {
    "enabled": True,
    "server": "",            # leer = Add-on-Option ntfy_server
    "topic": "",             # leer = Add-on-Option ntfy_topic
    "tasks_enabled": True,
    "tasks_time": "08:00",
    "climate_enabled": True,
    "climate_minutes": 30,   # so lange muss ein Wert außerhalb liegen, bevor gewarnt wird
    "climate_strict": False, # False = erst bei deutlicher Abweichung ("schlecht"), True = jede Abweichung
    "climate_repeat_hours": 3,
    "sensor_offline_minutes": 30,
}


def _addon_options() -> dict:
    p = DATA_DIR / "options.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except json.JSONDecodeError:
        return {}


def settings(session: Session) -> dict:
    s = session.get(Setting, "notify")
    cfg = {**DEFAULTS, **(s.value if s else {})}
    opt = _addon_options()
    cfg["server_effective"] = (cfg["server"] or opt.get("ntfy_server") or "https://ntfy.sh").rstrip("/")
    cfg["topic_effective"] = (cfg["topic"] or opt.get("ntfy_topic") or "").strip()
    return cfg


def save_settings(session: Session, data: dict) -> dict:
    s = session.get(Setting, "notify") or Setting(key="notify")
    cur = {**DEFAULTS, **(s.value or {})}
    for k in DEFAULTS:
        if k in data:
            cur[k] = data[k]
    s.value = cur
    session.add(s)
    session.commit()
    return settings(session)


def ready(cfg: dict) -> bool:
    return bool(cfg["enabled"] and cfg["topic_effective"])


async def send(cfg: dict, title: str, message: str, priority: int = 3, tags: Optional[list] = None,
               click: Optional[str] = None) -> bool:
    """Veröffentlicht per JSON an die Server-Wurzel (UTF-8-sicher für Umlaute im Titel)."""
    if not cfg["topic_effective"]:
        return False
    body = {"topic": cfg["topic_effective"], "title": title, "message": message, "priority": priority,
            "tags": tags or []}
    if click:
        body["click"] = click
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(cfg["server_effective"], json=body)
        if r.status_code >= 400:
            log.warning("ntfy antwortet %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except httpx.HTTPError as e:
        log.warning("ntfy nicht erreichbar: %s", e)
        return False


# ------------------------------------------------------------------ Aufgaben

def task_digest(session: Session, today: Optional[date] = None) -> Optional[tuple[str, str]]:
    today = today or date.today()
    tasks = services.tasks_due(session, today=today)
    if not tasks:
        return None
    lines = []
    for t in tasks:
        late = (today - t.due_on).days
        lines.append(f"• {t.title}" + (f" (seit {late} {'Tag' if late == 1 else 'Tagen'} überfällig)" if late > 0 else ""))
    n = len(tasks)
    return (f"Grow: {n} Aufgabe{'n' if n != 1 else ''} fällig", "\n".join(lines))


def _tasks_due_now(cfg: dict, last_sent: Optional[str], now: datetime) -> bool:
    try:
        hh, mm = (int(x) for x in str(cfg["tasks_time"]).split(":")[:2])
    except ValueError:
        hh, mm = 8, 0
    return now.time() >= now.replace(hour=hh, minute=mm).time() and last_sent != now.date().isoformat()


async def tasks_job(session: Session, now: Optional[datetime] = None) -> bool:
    """Läuft alle paar Minuten; schickt die Liste einmal täglich ab der eingestellten Uhrzeit
    (auch nach einem Neustart, wenn der Zeitpunkt verpasst wurde)."""
    now = now or datetime.now()
    cfg = settings(session)
    if not (ready(cfg) and cfg["tasks_enabled"]):
        return False
    st = session.get(Setting, "notify_state") or Setting(key="notify_state", value={})
    if not _tasks_due_now(cfg, (st.value or {}).get("tasks_sent_on"), now):
        return False
    d = task_digest(session, now.date())
    ok = True if not d else await send(cfg, d[0], d[1], priority=3, tags=["seedling", "clipboard"])
    if ok:  # bei Fehlschlag beim nächsten Lauf erneut versuchen
        st.value = {**(st.value or {}), "tasks_sent_on": now.date().isoformat()}
        session.add(st)
        session.commit()
    return bool(d) and ok


# ------------------------------------------------------------------ Klima-Alarm

# Laufzeit-Zustand pro (setup_id, art): seit wann außerhalb, wann zuletzt gewarnt, letzter Wert
_state: dict[tuple, dict] = {}


def lead_phase(session: Session, setup_id: int, today: Optional[date] = None) -> Optional[str]:
    """Phase der ersten aktiven Pflanze mit Klima-Zielbereich (wie die Heute-Ansicht)."""
    runs = session.exec(select(Run).where(Run.status == "aktiv", Run.setup_id == setup_id)
                        .order_by(Run.start_date.desc())).all()
    for run in runs:
        for p in session.exec(select(Plant).where(Plant.run_id == run.id, Plant.status == "aktiv").order_by(Plant.id)):
            ph = services.phase_of(session, p, today).phase
            if ph in climate.VPD_TARGETS:
                return ph
    return None


PHASE_NAMES = {"seedling": "Sämling", "veg": "Wachstum", "bloom": "Blüte", "flush": "Spülen"}


def evaluate(sample: Optional[ClimateSample], phase: Optional[str], strict: bool) -> dict[str, dict]:
    """Liefert je Messgröße {'bad': bool, 'value', 'target'}; ohne Phase keine Bewertung."""
    if not sample or not phase:
        return {}
    out = {}
    v = climate.vpd_leaf(sample.temp, sample.rh) or sample.vpd
    for key, val, rng in (("temp", sample.temp, climate.TEMP_TARGETS.get(phase)),
                          ("vpd", v, climate.VPD_TARGETS.get(phase))):
        r = climate.rate(val, rng)
        if r == "unbekannt":
            continue
        out[key] = {"bad": r == "schlecht" or (strict and r != "ok"), "value": val, "target": rng}
    return out


def _fmt(key: str, val: float) -> str:
    return f"{val:.1f} °C".replace(".", ",") if key == "temp" else f"{val:.2f} kPa".replace(".", ",")


LABEL = {"temp": "Temperatur", "vpd": "VPD (Blatt)"}


def climate_messages(setup_id: int, sample: Optional[ClimateSample], phase: Optional[str], cfg: dict,
                     now: Optional[datetime] = None) -> list[dict]:
    """Zustandsautomat; gibt zu sendende Meldungen zurück. Getrennt von send() für Tests."""
    now = now or datetime.now()
    msgs = []
    need = timedelta(minutes=int(cfg["climate_minutes"]))
    repeat = timedelta(hours=float(cfg["climate_repeat_hours"]))

    # Sensor liefert nichts
    off = _state.setdefault((setup_id, "offline"), {})
    if sample is None:
        off.setdefault("since", now)
        if now - off["since"] >= timedelta(minutes=int(cfg["sensor_offline_minutes"])) and \
                (not off.get("alerted") or now - off["alerted"] >= repeat):
            off["alerted"] = now
            msgs.append({"title": "Grow: Klimasensor liefert keine Werte",
                         "message": f"Seit {off['since']:%H:%M} keine Temperatur/Luftfeuchte aus Home Assistant.",
                         "priority": 4, "tags": ["warning"]})
        return msgs
    if off.get("alerted"):
        msgs.append({"title": "Grow: Klimasensor wieder da", "message": "Werte kommen wieder an.",
                     "priority": 2, "tags": ["white_check_mark"]})
    off.clear()

    for key, ev in evaluate(sample, phase, bool(cfg["climate_strict"])).items():
        st = _state.setdefault((setup_id, key), {})
        lo, hi = ev["target"]
        target = f"{_fmt(key, lo)} – {_fmt(key, hi)}"
        if ev["bad"]:
            st.setdefault("since", now)
            if now - st["since"] >= need and (not st.get("alerted") or now - st["alerted"] >= repeat):
                st["alerted"] = now
                direction = "zu niedrig" if ev["value"] < lo else "zu hoch"
                mins = int((now - st["since"]).total_seconds() // 60)
                msgs.append({"title": f"Grow: {LABEL[key]} {direction}",
                             "message": f"{_fmt(key, ev['value'])} seit {mins} min, Ziel {PHASE_NAMES.get(phase, phase)}: {target}.",
                             "priority": 4, "tags": ["thermometer" if key == "temp" else "droplet", "warning"]})
        else:
            if st.get("alerted"):
                msgs.append({"title": f"Grow: {LABEL[key]} wieder im Bereich",
                             "message": f"{_fmt(key, ev['value'])}, Ziel {target}.",
                             "priority": 2, "tags": ["white_check_mark"]})
            st.clear()
    return msgs


async def climate_check(session: Session, setup_id: int, sample: Optional[ClimateSample]) -> int:
    cfg = settings(session)
    if not (ready(cfg) and cfg["climate_enabled"]):
        return 0
    msgs = climate_messages(setup_id, sample, lead_phase(session, setup_id), cfg)
    for m in msgs:
        await send(cfg, **m)
    return len(msgs)


def status(session: Session) -> dict:
    cfg = settings(session)
    return {**cfg, "ready": ready(cfg),
            "alarms": [{"setup_id": k[0], "kind": k[1], "since": v["since"].isoformat() if v.get("since") else None,
                        "alerted": v["alerted"].isoformat() if v.get("alerted") else None}
                       for k, v in _state.items() if v.get("since")]}
