"""Zusammenführung von Daten und Logik für die API."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from .logic import feeding, light, phases, space
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
    for (stage, _f, _b), ctxs in groups.items():
        sched = schedule_for_stage(session, run.schedule_id, stage)
        r = feeding.build_recipe(ctxs, vols, sched, products, soil, water, today, extras, lights_on)
        out.append(r)
    return out


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
    return {
        "plant": plant.model_dump(),
        "strain": strain.model_dump() if strain else None,
        "phase": ph.dict(),
        "last_watering": {"ts": last_water.ts.isoformat(), "volume_l": last_water.volume_l, "type": last_water.type,
                          "days_ago": (today - last_water.ts.date()).days} if last_water else None,
        "last_photo_id": last_photo.id if last_photo else None,
        "space": sp,
        "actions": actions,
    }


def next_actions(plant: Plant, ph: phases.PhaseInfo, last_water, today: date) -> list[str]:
    a = []
    if ph.phase == "einweichen":
        a.append("Samen einsetzen und Datum unter „Gesetzt“ eintragen.")
    elif ph.phase == "keimung":
        a.append("Erde feucht, nicht nass halten. Sobald der Keimling sichtbar ist: „Aufgelaufen“ eintragen.")
    elif ph.phase == "seedling":
        a.append("Nur im Ring um den Keimling gießen (0,1–0,3 l).")
    if ph.phase == "veg" and not plant.preflower_on and ph.preflower_date and (ph.preflower_date - today).days <= 7:
        a.append("Auf Vorblüte achten (weiße Härchen an den Nodien) und bestätigen.")
    if ph.phase == "veg" and ph.week and 3 <= ph.week <= 5:
        a.append("LST: Haupttrieb sanft herunterbinden (bei Autos statt Toppen).")
    if ph.phase == "flush":
        a.append("Nur noch Wasser. Trichome prüfen.")
    if ph.phase == "harvest":
        a.append("Erntereif laut Plan – Trichome prüfen (milchig/bernstein).")
    if last_water and ph.phase not in ("einweichen", "geplant"):
        d = (today - last_water.ts.date()).days
        if d >= 3:
            a.append(f"Letztes Gießen vor {d} Tagen – Topf prüfen (Gewicht/Fingerprobe).")
    return a


def tasks_due(session: Session, run_id: Optional[int] = None, today: Optional[date] = None) -> list[Task]:
    today = today or date.today()
    q = select(Task).where(Task.active == True, Task.due_on <= today)  # noqa: E712
    if run_id:
        q = q.where((Task.run_id == run_id) | (Task.run_id == None))  # noqa: E711
    return list(session.exec(q.order_by(Task.due_on)))
