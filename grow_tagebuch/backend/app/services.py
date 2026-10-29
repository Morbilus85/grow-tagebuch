"""Zusammenführung von Daten und Logik für die API."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from .logic import feeding, light, phases, space, training
from .models import (
    FeedingSchedule,
    LightCalibration,
    LogEntry,
    Photo,
    Plant,
    Product,
    Run,
    ScheduleEntry,
    Setup,
    SoilProfile,
    Strain,
    Task,
    TrainingTechnique,
    WaterProfile,
)

PHASE_GROUP = {"seedling": "seedling", "veg": "veg", "bloom": "bloom", "flush": "flush"}


def phase_of(session: Session, plant: Plant, today: Optional[date] = None) -> phases.PhaseInfo:
    strain = session.get(Strain, plant.strain_id) if plant.strain_id else None
    return phases.compute(plant, strain, today)


def recent_logs(session: Session, plant_id: int, days: int = 21) -> list[LogEntry]:
    since = datetime.now() - timedelta(days=days)
    return list(session.exec(select(LogEntry).where(LogEntry.plant_id == plant_id, LogEntry.ts >= since)
                             .order_by(LogEntry.ts.desc())))


def light_model(session: Session, setup_id: int) -> light.LightModel:
    pts = session.exec(select(LightCalibration).where(LightCalibration.setup_id == setup_id)).all()
    return light.LightModel(pts)


def heights(session: Session, plant_id: int) -> list[tuple[date, float]]:
    rows = session.exec(select(LogEntry).where(LogEntry.plant_id == plant_id, LogEntry.height_cm != None)  # noqa: E711
                        .order_by(LogEntry.ts)).all()
    return [(r.ts.date(), r.height_cm) for r in rows]


def plant_ctx(session: Session, plant: Plant, today: date) -> feeding.PlantCtx:
    ph = phase_of(session, plant, today)
    ref = plant.planted_on or plant.sprouted_on or today
    preflower_reached = bool(plant.preflower_on) or ph.phase in ("bloom", "flush", "harvest")
    return feeding.PlantCtx(
        plant_id=plant.id, name=plant.name, stage=ph.schedule_stage, phase=ph.phase, bloom_week=ph.bloom_week,
        preflower_confirmed_or_reached=preflower_reached, weeks_in_soil=(today - ref).days / 7,
        feed_factor=plant.feed_factor, mg_flag=plant.mg_deficiency_flag, recent_logs=recent_logs(session, plant.id),
    )


def schedule_for_stage(session: Session, schedule_id: Optional[int], stage: Optional[str]) -> dict[str, float]:
    if not schedule_id or not stage or stage == "flush":
        return {}
    rows = session.exec(select(ScheduleEntry).where(ScheduleEntry.schedule_id == schedule_id, ScheduleEntry.stage == stage)).all()
    return {r.product_key: r.dose_per_l for r in rows}


def recipes(session: Session, run: Run, volumes: dict[int, float], extras=None, today: Optional[date] = None,
            lights_on: Optional[bool] = None) -> list[dict]:
    today = today or date.today()
    products = {p.key: p for p in session.exec(select(Product)).all()}
    soil = session.get(SoilProfile, run.soil_id) if run.soil_id else None
    water = session.get(WaterProfile, run.water_id) if run.water_id else None
    groups: dict[tuple, list] = {}
    for pid, vol in volumes.items():
        plant = session.get(Plant, int(pid))
        if not plant or plant.run_id != run.id or not vol:
            continue
        ctx = plant_ctx(session, plant, today)
        f, _, blocked = feeding.feed_factor(ctx, soil, today)
        groups.setdefault((ctx.stage, f, blocked), []).append(ctx)
    out = []
    vols = {int(k): float(v) for k, v in volumes.items()}
    from .models import Setting
    mode = session.get(Setting, "ls_mode")
    ls_vegan = bool(mode and mode.value.get("mode") == "vegan")
    for (stage, _f, _b), ctxs in groups.items():
        sched = schedule_for_stage(session, run.schedule_id, stage)
        r = feeding.build_recipe(ctxs, vols, sched, products, soil, water, today, extras, lights_on, ls_vegan)
        out.append(r)
    return out


def latest_nodes(session: Session, plant_id: int) -> Optional[int]:
    r = session.exec(select(LogEntry).where(LogEntry.plant_id == plant_id, LogEntry.nodes != None)  # noqa: E711
                     .order_by(LogEntry.ts.desc())).first()
    return r.nodes if r else None


def plant_training(session: Session, plant: Plant, ph=None, space_status: str = "ok",
                   today: Optional[date] = None) -> list[dict]:
    today = today or date.today()
    ph = ph or phase_of(session, plant, today)
    strain = session.get(Strain, plant.strain_id) if plant.strain_id else None
    techs = {t.key: t for t in session.exec(select(TrainingTechnique)).all()}
    last_stress = None
    for l in session.exec(select(LogEntry).where(LogEntry.plant_id == plant.id, LogEntry.technique_key != None)  # noqa: E711
                          .order_by(LogEntry.ts.desc())).all():
        t = techs.get(l.technique_key)
        if t and t.recovery_days and t.stress in ("mittel", "hoch"):
            last_stress = (l.ts.date(), t.recovery_days, t.name)
            break
    nodes = latest_nodes(session, plant.id)
    res = [training.evaluate(t, auto=strain.auto if strain else True, phase=ph.phase, day=ph.day,
                             bloom_week=ph.bloom_week, nodes=nodes, last_stress=last_stress,
                             space_status=space_status, today=today) for t in techs.values()]
    return training.rank(res)


def plant_status(session: Session, plant: Plant, run: Run, setup: Optional[Setup], today: Optional[date] = None) -> dict:
    today = today or date.today()
    ph = phase_of(session, plant, today)
    strain = session.get(Strain, plant.strain_id) if plant.strain_id else None
    logs = session.exec(select(LogEntry).where(LogEntry.plant_id == plant.id).order_by(LogEntry.ts.desc())).all()
    last_water = next((l for l in logs if l.type in ("watering", "feeding")), None)
    last_photo = None
    for l in logs:
        p = session.exec(select(Photo).where(Photo.log_id == l.id).order_by(Photo.id.desc())).first()
        if p:
            last_photo = p
            break
    hs = heights(session, plant.id)
    group = PHASE_GROUP.get(ph.phase)
    model = light_model(session, run.setup_id)
    rec = model.recommend(group, run.light_hours, limit=1) if group else []
    sp = space.assess(setup.height_cm if setup else None, setup.lamp_hang_cm if setup else 15, plant.pot_height_cm, hs,
                      rec[0]["distance_cm"] if rec else None, strain.auto if strain else True, ph.week,
                      strain.max_height_cm if strain else None)
    actions = next_actions(plant, ph, last_water, today)
    tr = plant_training(session, plant, ph, sp["status"], today) if ph.day else []
    now_list = [t for t in tr if t["status"] == "jetzt" and t["suitability"] != "abraten"]
    return {
        "plant": plant.model_dump(),
        "strain": strain.model_dump() if strain else None,
        "phase": ph.dict(),
        "last_watering": {"ts": last_water.ts.isoformat(), "volume_l": last_water.volume_l, "type": last_water.type,
                          "days_ago": (today - last_water.ts.date()).days} if last_water else None,
        "last_photo_id": last_photo.id if last_photo else None,
        "last_log": {"id": logs[0].id, "type": logs[0].type, "ts": logs[0].ts.isoformat(), "text": logs[0].text[:80]} if logs else None,
        "space": sp,
        "actions": actions,
        "nodes": latest_nodes(session, plant.id),
        "germination": germination(plant),
        "training_now": [{"key": t["key"], "name": t["name"], "priority": t["priority"], "suitability": t["suitability"]}
                         for t in now_list[:4]],
        "training_wait": next(({"name": t["name"], "reason": t["reasons"][0]} for t in tr if t["status"] == "warten"), None),
    }


def germination(plant: Plant, now_dt: Optional[datetime] = None) -> Optional[dict]:
    """Aktueller Schritt der Keimung nach Methode und Zeit."""
    from .germination_data import AFTER_PLANTING, METHODS
    if plant.sprouted_on or plant.harvested_on:
        return None
    now_dt = now_dt or datetime.now()
    m = next((x for x in METHODS if x["key"] == plant.germ_method), None)
    out = {"method_key": plant.germ_method, "method_name": m["name"] if m else None, "stage": None, "hint": None,
           "next_hint": None, "next_in_hours": None}
    if plant.planted_on:
        days = (now_dt.date() - plant.planted_on).days
        cur = [e for e in AFTER_PLANTING if e["day"] <= days]
        nxt = [e for e in AFTER_PLANTING if e["day"] > days]
        out.update(stage="in_erde", elapsed=f"Tag {days + 1} nach dem Einsetzen", hint=cur[-1]["text"] if cur else None)
        if nxt:
            out.update(next_hint=nxt[0]["text"], next_in_hours=(nxt[0]["day"] - days) * 24)
        return out
    start = plant.soaked_at or (datetime.combine(plant.soaked_on, datetime.min.time()) if plant.soaked_on else None)
    if not start:
        out.update(stage="geplant", hint="Keimmethode wählen und Einweichen starten." if not m else f"Bereit: {m['name']}.")
        return out
    hours = (now_dt - start).total_seconds() / 3600
    tl = (m or {}).get("timeline") or []
    cur = [e for e in tl if e["hours"] <= hours]
    nxt = [e for e in tl if e["hours"] > hours]
    out.update(stage="einweichen", hours=round(hours, 1), elapsed=f"seit {int(hours)} Stunden",
               hint=cur[-1]["text"] if cur else ("Sobald eine Keimwurzel sichtbar ist: einsetzen und „Gesetzt“ eintragen." if not tl else None))
    if nxt:
        out.update(next_hint=nxt[0]["text"], next_in_hours=round(nxt[0]["hours"] - hours, 1))
    return out


def next_actions(plant: Plant, ph: phases.PhaseInfo, last_water, today: date) -> list[str]:
    a = []
    g = germination(plant)
    if ph.phase in ("einweichen", "keimung", "geplant"):
        if g and g.get("hint"):
            a.append(g["hint"])
        if ph.phase == "keimung":
            a.append("Sobald der Keimling sichtbar ist: „Aufgelaufen“ eintragen.")
    elif ph.phase == "seedling":
        a.append("Nur im Ring um den Keimling gießen (0,1–0,3 l).")
    if ph.phase == "veg" and not plant.preflower_on and ph.preflower_date and (ph.preflower_date - today).days <= 7:
        a.append("Auf Vorblüte achten (weiße Härchen an den Nodien) und bestätigen.")
    if ph.phase == "flush":
        a.append("Nur noch Wasser. Trichome prüfen.")
    if ph.phase == "harvest":
        a.append("Erntereif laut Plan – Trichome prüfen (milchig/bernstein).")
    if last_water and ph.phase not in ("einweichen", "geplant"):
        d = (today - last_water.ts.date()).days
        if d >= 3:
            a.append(f"Letztes Gießen vor {d} Tagen – Topf prüfen (Gewicht/Fingerprobe).")
    return a


KCANG_PLANTS_PER_ADULT = 3
KCANG_HOME_GRAMS_PER_ADULT = 50


def household(session: Session) -> dict:
    from .models import Setting
    s = session.get(Setting, "household")
    return {"adults": 1, **(s.value if s else {})}


def legal_status(session: Session) -> dict:
    """Lebende Pflanzen = gesetzt/aufgelaufen und nicht geerntet oder eingegangen."""
    adults = max(int(household(session).get("adults") or 1), 1)
    living = session.exec(select(Plant).where(Plant.status == "aktiv", Plant.harvested_on == None)).all()  # noqa: E711
    count = sum(1 for p in living if p.planted_on or p.sprouted_on)
    limit = adults * KCANG_PLANTS_PER_ADULT
    status = "ok" if count < limit else "voll" if count == limit else "ueber"
    return {"adults": adults, "living_plants": count, "plant_limit": limit, "status": status,
            "home_storage_limit_g": adults * KCANG_HOME_GRAMS_PER_ADULT}


def tasks_due(session: Session, run_id: Optional[int] = None, today: Optional[date] = None) -> list[Task]:
    today = today or date.today()
    q = select(Task).where(Task.active == True, Task.due_on <= today)  # noqa: E712
    if run_id:
        q = q.where((Task.run_id == run_id) | (Task.run_id == None))  # noqa: E711
    return list(session.exec(q.order_by(Task.due_on)))
