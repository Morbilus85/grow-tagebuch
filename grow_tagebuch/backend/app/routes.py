"""REST-API (alle Pfade relativ, damit sie hinter HA-Ingress funktionieren)."""
from __future__ import annotations

import io
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional, get_args

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel
from sqlmodel import Session, select

from . import services
from .db import PHOTO_DIR, get_session
from .logic import climate, light
from .models import (
    ClimateSample,
    Equipment,
    FeedingSchedule,
    LightCalibration,
    LogEntry,
    Photo,
    Plant,
    Product,
    Run,
    ScheduleEntry,
    SensorMapping,
    Setup,
    SoilProfile,
    Strain,
    Task,
    TrainingTechnique,
    WaterProfile,
    now,
)

api = APIRouter(prefix="/api")
log = logging.getLogger("grow.api")

try:  # HEIC/HEIF-Fotos (iPhone, einige Android-Kameras)
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # pragma: no cover
    pass
S = Depends(get_session)
MAX_PX = 2560


def _get(session: Session, model, oid: int):
    obj = session.get(model, oid)
    if not obj:
        raise HTTPException(404, f"{model.__name__} {oid} nicht gefunden")
    return obj


def _apply(obj, data: dict, exclude=("id",)):
    for k, v in data.items():
        if k in exclude or not hasattr(obj, k):
            continue
        field = type(obj).model_fields.get(k)
        if field is not None and isinstance(v, str):
            types = set(get_args(field.annotation)) | {field.annotation}
            if datetime in types:
                v = datetime.fromisoformat(v) if v else None
            elif date in types:
                v = date.fromisoformat(v[:10]) if v else None
        setattr(obj, k, v)
    return obj


# ------------------------------------------------------------------ Übersicht

@api.get("/today")
async def today(session: Session = S):
    runs = session.exec(select(Run).where(Run.status == "aktiv").order_by(Run.start_date.desc())).all()
    out = []
    for run in runs:
        setup = session.get(Setup, run.setup_id)
        plants = session.exec(select(Plant).where(Plant.run_id == run.id, Plant.status == "aktiv").order_by(Plant.id)).all()
        statuses = [services.plant_status(session, p, run, setup) for p in plants]
        live = await climate.read_live(session, run.setup_id)
        lead_phase = next((s["phase"]["phase"] for s in statuses if s["phase"]["phase"] in climate.VPD_TARGETS), None)
        vpd_rng = climate.VPD_TARGETS.get(lead_phase)
        t_rng = climate.TEMP_TARGETS.get(lead_phase)
        live["vpd_target"] = vpd_rng
        live["temp_target"] = t_rng
        live["vpd_rating"] = climate.rate(live.get("vpd_leaf") or live.get("vpd"), vpd_rng)
        live["temp_rating"] = climate.rate(live.get("temp"), t_rng)
        model = services.light_model(session, run.setup_id)
        lgroup = services.PHASE_GROUP.get(lead_phase or "seedling", "seedling")
        live_level = live.get("light_level")
        level = int(live_level) if live_level else run.light_level
        la = light.assess(model, lgroup, level, run.lamp_distance_cm, run.light_hours)
        la["phase_group"] = lgroup
        la["level"] = level
        la["level_source"] = "controller" if live_level else "eingestellt"
        la["distance_cm"] = run.lamp_distance_cm
        la["lamp_on"] = live.get("light_on")
        if live.get("light_on") is False:
            la["messages"].insert(0, "Lampe ist laut Controller gerade aus. Werte gelten für die eingestellte Stufe, wenn sie an ist.")
        la["recommendations"] = model.recommend(lgroup, run.light_hours)
        out.append({
            "run": run.model_dump(),
            "setup": setup.model_dump() if setup else None,
            "plants": statuses,
            "climate": live,
            "light": la,
            "tasks": [t.model_dump() for t in services.tasks_due(session, run.id)],
            "cases": services.open_cases(session, run.id),
        })
    return {"date": date.today().isoformat(), "runs": out, "legal": services.legal_status(session)}


# ------------------------------------------------------------------ Runs & Pflanzen

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Frühling", 4: "Frühling", 5: "Frühling",
           6: "Sommer", 7: "Sommer", 8: "Sommer", 9: "Herbst", 10: "Herbst", 11: "Herbst"}


def _season(d: date) -> str:
    if d.month == 12:
        return f"Winter {d.year}/{str(d.year + 1)[2:]}"
    if d.month <= 2:
        return f"Winter {d.year - 1}/{str(d.year)[2:]}"
    return f"{SEASONS[d.month]} {d.year}"


def _auto_name(session: Session, strain_ids: list, on: date, exclude_id: Optional[int] = None) -> str:
    """„Sorte – Saison Jahr“, bei Dopplung mit laufender Nummer."""
    names = []
    for sid in strain_ids:
        st = session.get(Strain, sid) if sid else None
        if st and st.name not in names:
            names.append(st.name)
    head = names[0] if len(names) == 1 else (f"{names[0]} & {names[1]}" if len(names) == 2 else ("Mischgrow" if names else "Grow"))
    base = f"{head} – {_season(on)}"
    taken = {r.name for r in session.exec(select(Run)).all() if r.id != exclude_id}
    name, n = base, 2
    while name in taken:
        name, n = f"{base} ({n})", n + 1
    return name


@api.get("/runs")
def list_runs(session: Session = S):
    return session.exec(select(Run).order_by(Run.start_date.desc())).all()


@api.get("/runs/{rid}")
def get_run(rid: int, session: Session = S):
    run = _get(session, Run, rid)
    plants = session.exec(select(Plant).where(Plant.run_id == rid).order_by(Plant.id)).all()
    return {"run": run, "plants": plants}


@api.post("/runs")
def create_run(data: dict, session: Session = S):
    if not (data.get("name") or "").strip():
        data = {k: v for k, v in data.items() if k != "name"}
        run = _apply(Run(name=_auto_name(session, [], date.today()), setup_id=data["setup_id"], start_date=date.today(),
                         name_auto=True), data)
    else:
        run = _apply(Run(name=data["name"], setup_id=data["setup_id"], start_date=date.today()), data)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@api.patch("/runs/{rid}")
def update_run(rid: int, data: dict, session: Session = S):
    run = _get(session, Run, rid)
    if "name" in data and data["name"] != run.name:
        run.name_auto = False
    run = _apply(run, data)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _abort_plant(session: Session, plant: Plant, reason: str, on: date) -> None:
    """Pflanze beenden: Status, Datum, Tagebucheintrag, aus Einzelpflanzen-Fällen lösen."""
    from .models import PestCase
    plant.status = "abgebrochen"
    plant.ended_on = on
    plant.end_reason = reason
    session.add(plant)
    session.add(LogEntry(run_id=plant.run_id, plant_id=plant.id, type="phase",
                         text=f"Abgebrochen am {on.strftime('%d.%m.%Y')}" + (f": {reason}" if reason else "")))
    for c in session.exec(select(PestCase).where(PestCase.run_id == plant.run_id, PestCase.scope == "pflanzen",
                                                 PestCase.status != "erledigt")).all():
        if plant.id not in (c.plant_ids or []):
            continue
        c.plant_ids = [x for x in c.plant_ids if x != plant.id]
        if not c.plant_ids:
            c.status, c.closed_on = "erledigt", on
            for t in session.exec(select(Task).where(Task.case_id == c.id, Task.active == True)).all():  # noqa: E712
                t.active = False
                session.add(t)
        session.add(c)


def _on(data: dict) -> date:
    return date.fromisoformat(data["on"][:10]) if data.get("on") else date.today()


@api.post("/plants/{pid}/abort")
def abort_plant(pid: int, data: dict, session: Session = S):
    plant = _get(session, Plant, pid)
    if plant.status != "aktiv":
        raise HTTPException(400, f"{plant.name} ist nicht mehr aktiv ({plant.status})")
    _abort_plant(session, plant, (data.get("reason") or "").strip(), _on(data))
    session.commit()
    session.refresh(plant)
    return plant


@api.post("/plants/{pid}/reactivate")
def reactivate_plant(pid: int, session: Session = S):
    plant = _get(session, Plant, pid)
    plant.status, plant.ended_on, plant.end_reason = "aktiv", None, ""
    session.add(plant)
    session.add(LogEntry(run_id=plant.run_id, plant_id=plant.id, type="phase", text="Wieder aktiviert"))
    session.commit()
    session.refresh(plant)
    return plant


def _add_seeds(session: Session, run: Run, data: dict) -> list:
    rows = data.get("rows") or ([{"strain_id": data.get("strain_id"), "count": data.get("plants") or data.get("count")}]
                                if (data.get("plants") or data.get("count")) else [])
    soaked_at = datetime.fromisoformat(data["soaked_at"]) if data.get("soaked_at") else None
    existing = len(session.exec(select(Plant).where(Plant.run_id == run.id)).all())
    created = []
    for row in rows:
        for _ in range(int(row.get("count") or 0)):
            existing += 1
            p = Plant(run_id=run.id, name=f"Pflanze {existing}", strain_id=row.get("strain_id"),
                      germ_method=data.get("germ_method"), pot_l=data.get("pot_l"),
                      pot_height_cm=int(data.get("pot_height_cm") or 30), soaked_at=soaked_at,
                      soaked_on=soaked_at.date() if soaked_at else None)
            session.add(p)
            created.append(p)
    if run.name_auto and created:
        ids = [p.strain_id for p in session.exec(select(Plant).where(Plant.run_id == run.id)).all()] + [p.strain_id for p in created]
        run.name = _auto_name(session, ids, run.start_date, exclude_id=run.id)
        session.add(run)
    return created


@api.post("/runs/{rid}/seeds")
def add_seeds(rid: int, data: dict, session: Session = S):
    """Neue Samen in einen Durchgang eintragen (nach Neustart oder neuem Durchgang)."""
    run = _get(session, Run, rid)
    created = _add_seeds(session, run, data)
    if not created:
        raise HTTPException(400, "Keine Samen angegeben")
    session.commit()
    session.refresh(run)
    legal = services.legal_status(session)
    out = {"run": run.model_dump(mode="json"),
           "plants": [p.model_dump(mode="json") for p in session.exec(select(Plant).where(Plant.run_id == rid)).all()]}
    if legal["status"] == "ueber":
        out["warning"] = (f"Achtung: {legal['living_plants']} lebende Pflanzen, erlaubt sind {legal['plant_limit']} "
                          f"({legal['adults']} Erwachsene × 3 nach KCanG).")
    return out


@api.post("/runs/{rid}/abort")
def abort_run(rid: int, data: dict, session: Session = S):
    """Ganzen Durchgang abbrechen. Optional direkt neu starten: gleiche Einstellungen,
    offene Aufgaben und zeltweite Schädlingsfälle wandern in den neuen Durchgang."""
    from .models import PestCase
    run = _get(session, Run, rid)
    reason = (data.get("reason") or "").strip()
    on = _on(data)
    for p in session.exec(select(Plant).where(Plant.run_id == rid, Plant.status == "aktiv")).all():
        _abort_plant(session, p, reason, on)
    run.status, run.ended_on, run.end_reason = "abgebrochen", on, reason
    session.add(run)
    session.add(LogEntry(run_id=rid, type="note", text=f"Durchgang abgebrochen" + (f": {reason}" if reason else "")))
    out: dict[str, Any] = {"aborted": rid, "new_run": None, "plants": []}
    restart = data.get("restart")
    if restart:
        restart = restart if isinstance(restart, dict) else {}
        prev_strains = [p.strain_id for p in session.exec(select(Plant).where(Plant.run_id == rid)).all()]
        new = Run(name=restart.get("name") or _auto_name(session, prev_strains, on), name_auto=not restart.get("name"),
                  setup_id=run.setup_id, soil_id=run.soil_id,
                  water_id=run.water_id, schedule_id=run.schedule_id, start_date=on, light_hours=run.light_hours,
                  light_on_time=run.light_on_time, light_level=run.light_level, lamp_distance_cm=run.lamp_distance_cm,
                  notes=f"Neustart nach Abbruch von „{run.name}“" + (f" ({reason})" if reason else ""))
        session.add(new)
        session.flush()
        for t in session.exec(select(Task).where(Task.run_id == rid, Task.active == True)).all():  # noqa: E712
            t.run_id = new.id
            session.add(t)
        for c in session.exec(select(PestCase).where(PestCase.run_id == rid, PestCase.status != "erledigt")).all():
            if c.scope == "zelt":
                c.run_id = new.id
                session.add(c)
                for t in session.exec(select(Task).where(Task.case_id == c.id)).all():
                    t.run_id = new.id
                    session.add(t)
        _add_seeds(session, new, restart)
        session.commit()
        session.refresh(new)
        out["new_run"] = new.model_dump(mode="json")
        out["plants"] = [p.model_dump(mode="json") for p in
                         session.exec(select(Plant).where(Plant.run_id == new.id)).all()]
    else:
        session.commit()
    return out


@api.get("/plants/{pid}")
def get_plant(pid: int, session: Session = S):
    plant = _get(session, Plant, pid)
    run = session.get(Run, plant.run_id)
    setup = session.get(Setup, run.setup_id)
    return services.plant_status(session, plant, run, setup)


@api.post("/plants")
def create_plant(data: dict, session: Session = S):
    plant = _apply(Plant(run_id=data["run_id"], name=data.get("name", "Pflanze")), data)
    session.add(plant)
    session.commit()
    session.refresh(plant)
    legal = services.legal_status(session)
    out = plant.model_dump(mode="json")
    if legal["status"] == "ueber":
        out["warning"] = (f"Achtung: {legal['living_plants']} lebende Pflanzen, erlaubt sind {legal['plant_limit']} "
                          f"({legal['adults']} Erwachsene × 3 nach KCanG).")
    return out


@api.get("/household")
def get_household(session: Session = S):
    return {**services.household(session), **services.legal_status(session)}


@api.put("/household")
def set_household(data: dict, session: Session = S):
    from .models import Setting
    s = session.get(Setting, "household") or Setting(key="household")
    s.value = {"adults": max(int(data.get("adults") or 1), 1)}
    session.add(s)
    session.commit()
    return get_household(session)


@api.patch("/plants/{pid}")
def update_plant(pid: int, data: dict, session: Session = S):
    plant = _apply(_get(session, Plant, pid), data)
    session.add(plant)
    session.commit()
    session.refresh(plant)
    return plant


@api.delete("/plants/{pid}")
def delete_plant(pid: int, session: Session = S):
    plant = _get(session, Plant, pid)
    for l in session.exec(select(LogEntry).where(LogEntry.plant_id == pid)).all():
        _delete_log(session, l)
    session.delete(plant)
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Tagebuch

def _log_dict(session: Session, l: LogEntry) -> dict:
    d = l.model_dump()
    d["ts"] = l.ts.isoformat()
    d["photos"] = [p.id for p in session.exec(select(Photo).where(Photo.log_id == l.id).order_by(Photo.id)).all()]
    return d


@api.get("/logs")
def list_logs(plant_id: Optional[int] = None, run_id: Optional[int] = None, limit: int = 200, session: Session = S):
    q = select(LogEntry)
    if plant_id:
        q = q.where(LogEntry.plant_id == plant_id)
    if run_id:
        q = q.where(LogEntry.run_id == run_id)
    rows = session.exec(q.order_by(LogEntry.ts.desc()).limit(limit)).all()
    return [_log_dict(session, l) for l in rows]


@api.get("/logs/{lid}")
def get_log(lid: int, session: Session = S):
    return _log_dict(session, _get(session, LogEntry, lid))


@api.post("/logs")
def create_log(data: dict, session: Session = S):
    if not data.get("run_id") and data.get("plant_id"):
        data["run_id"] = _get(session, Plant, data["plant_id"]).run_id
    l = _apply(LogEntry(run_id=data["run_id"], type=data.get("type", "note")), data)
    if not l.ts:
        l.ts = now()
    session.add(l)
    session.commit()
    session.refresh(l)
    return _log_dict(session, l)


@api.patch("/logs/{lid}")
def update_log(lid: int, data: dict, session: Session = S):
    l = _apply(_get(session, LogEntry, lid), data, exclude=("id", "run_id"))
    session.add(l)
    session.commit()
    session.refresh(l)
    return _log_dict(session, l)


def _delete_log(session: Session, l: LogEntry):
    for p in session.exec(select(Photo).where(Photo.log_id == l.id)).all():
        (PHOTO_DIR / p.filename).unlink(missing_ok=True)
        session.delete(p)
    session.delete(l)


@api.delete("/logs/{lid}")
def delete_log(lid: int, session: Session = S):
    _delete_log(session, _get(session, LogEntry, lid))
    session.commit()
    return {"ok": True}


@api.post("/logs/{lid}/photos")
async def upload_photo(lid: int, file: UploadFile = File(...), session: Session = S):
    _get(session, LogEntry, lid)
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Leere Datei")
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    except Exception as e:
        log.warning("Foto %s (%s, %d Bytes) nicht lesbar: %s", file.filename, file.content_type, len(raw), e)
        raise HTTPException(400, f"Bildformat nicht lesbar ({file.content_type or 'unbekannt'})")
    img.thumbnail((MAX_PX, MAX_PX))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    name = f"{datetime.now():%Y%m%d}_{uuid.uuid4().hex[:10]}.jpg"
    img.save(PHOTO_DIR / name, "JPEG", quality=85)
    thumb = img.copy()
    thumb.thumbnail((480, 480))
    thumb.save(PHOTO_DIR / f"t_{name}", "JPEG", quality=80)
    p = Photo(log_id=lid, filename=name, width=img.width, height=img.height)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@api.get("/photos/{phid}")
def get_photo(phid: int, thumb: bool = False, session: Session = S):
    p = _get(session, Photo, phid)
    path = PHOTO_DIR / (f"t_{p.filename}" if thumb else p.filename)
    if not path.exists():
        path = PHOTO_DIR / p.filename
    if not path.exists():
        raise HTTPException(404, "Fotodatei fehlt")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=604800"})


@api.delete("/photos/{phid}")
def delete_photo(phid: int, session: Session = S):
    p = _get(session, Photo, phid)
    (PHOTO_DIR / p.filename).unlink(missing_ok=True)
    (PHOTO_DIR / f"t_{p.filename}").unlink(missing_ok=True)
    session.delete(p)
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Gieß-/Düngeassistent

class RecipeReq(BaseModel):
    run_id: int
    volumes: dict[int, float]
    extras: list[dict] = []


@api.post("/feeding/recipe")
async def feeding_recipe(req: RecipeReq, session: Session = S):
    run = _get(session, Run, req.run_id)
    live = await climate.read_live(session, run.setup_id)
    return services.recipes(session, run, req.volumes, req.extras, lights_on=live.get("light_on"))


class ConfirmReq(BaseModel):
    run_id: int
    recipe: dict
    ph_in: Optional[float] = None
    ec_in: Optional[float] = None
    ph_down_ml_total: Optional[float] = None
    text: str = ""
    teas: list[str] = []


@api.post("/feeding/confirm")
def feeding_confirm(req: ConfirmReq, session: Session = S):
    items = req.recipe.get("items", [])
    total = req.recipe.get("total_l") or 0
    ph_down = round(req.ph_down_ml_total / total, 3) if req.ph_down_ml_total and total else None
    created = []
    for pl in req.recipe.get("plants", []):
        vol = pl.get("volume_l") or 0
        products = [{"product_key": it["key"], "name": it["name"], "per_l": it["per_l"], "unit": it["unit"],
                     "amount": round(it["per_l"] * vol, 2) if it.get("per_l") is not None else None,
                     "application": "giessen" if it.get("source") != "extra" else (it.get("note") or "giessen")}
                    for it in items]
        if ph_down:
            products.append({"product_key": "biobizz_bio_down", "name": "Bio-Down", "per_l": ph_down, "unit": "ml",
                             "amount": round(ph_down * vol, 2), "application": "giessen"})
        l = LogEntry(run_id=req.run_id, plant_id=pl["id"], type="feeding" if (items or req.teas) else "watering", volume_l=vol,
                     ph_in=req.ph_in, ec_in=req.ec_in, ph_down_ml_per_l=ph_down, products=products,
                     text=req.text, tags=[req.recipe.get("stage") or ""] + [f"tee:{t}" for t in req.teas])
        session.add(l)
        created.append(l)
    session.commit()
    return {"created": len(created)}


# ------------------------------------------------------------------ Klima & Licht

@api.get("/climate/{setup_id}/live")
async def climate_live(setup_id: int, session: Session = S):
    return await climate.read_live(session, setup_id)


@api.get("/climate/{setup_id}")
def climate_history(setup_id: int, hours: int = 48, session: Session = S):
    since = datetime.now() - timedelta(hours=hours)
    rows = session.exec(select(ClimateSample).where(ClimateSample.setup_id == setup_id, ClimateSample.ts >= since)
                        .order_by(ClimateSample.ts)).all()
    return [{"ts": r.ts.isoformat(), "temp": r.temp, "rh": r.rh, "vpd": r.vpd, "light": r.light_level,
             "heater": r.heater_on, "heatmat": r.heatmat_on} for r in rows]


@api.get("/light/{setup_id}")
def light_info(setup_id: int, hours: float = 20, session: Session = S):
    model = services.light_model(session, setup_id)
    table = []
    for dist in (30, 35, 40, 45, 50, 55, 60, 65, 70):
        row = {"distance_cm": dist}
        for lv in range(1, 11):
            p = model.ppfd(lv, dist)
            row[str(lv)] = p
        table.append(row)
    return {
        "calibrated": model.calibrated,
        "edge_factor": model.edge_factor,
        "measured_levels": model.levels_measured,
        "measured_distances": model.distances,
        "table": table,
        "targets": light.TARGETS,
        "recommendations": {ph: model.recommend(ph, hours) for ph in ("seedling", "veg", "bloom")},
        "points": session.exec(select(LightCalibration).where(LightCalibration.setup_id == setup_id)).all(),
    }


@api.post("/light/{setup_id}/calibration")
def add_calibration(setup_id: int, data: dict, session: Session = S):
    p = LightCalibration(setup_id=setup_id, measured_on=date.fromisoformat(data.get("measured_on") or date.today().isoformat()),
                         distance_cm=int(data["distance_cm"]), level=int(data["level"]), point=data.get("point", "A"),
                         ppfd=float(data["ppfd"]))
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


# ------------------------------------------------------------------ Stammdaten

@api.get("/setups")
def setups(session: Session = S):
    out = []
    for s in session.exec(select(Setup)).all():
        out.append({**s.model_dump(),
                    "equipment": session.exec(select(Equipment).where(Equipment.setup_id == s.id)).all(),
                    "sensors": session.exec(select(SensorMapping).where(SensorMapping.setup_id == s.id)).all()})
    return out


@api.patch("/setups/{sid}")
def update_setup(sid: int, data: dict, session: Session = S):
    s = _apply(_get(session, Setup, sid), data)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@api.delete("/setups/{sid}")
def delete_setup(sid: int, session: Session = S):
    s = _get(session, Setup, sid)
    if session.exec(select(Run).where(Run.setup_id == sid)).first():
        raise HTTPException(400, "Setup wird noch von einem Durchgang benutzt")
    for model in (Equipment, SensorMapping, LightCalibration, ClimateSample):
        for o in session.exec(select(model).where(model.setup_id == sid)).all():
            session.delete(o)
    session.delete(s)
    session.commit()
    return {"ok": True}


@api.put("/setups/{sid}/sensors")
def set_sensors(sid: int, data: dict[str, str], session: Session = S):
    for m in session.exec(select(SensorMapping).where(SensorMapping.setup_id == sid)).all():
        session.delete(m)
    for role, ent in data.items():
        if ent:
            session.add(SensorMapping(setup_id=sid, role=role, entity_id=ent))
    session.commit()
    return {"ok": True}


@api.get("/products")
def products(session: Session = S):
    return session.exec(select(Product).order_by(Product.in_stock.desc(), Product.brand, Product.name)).all()


@api.patch("/products/{pid}")
def update_product(pid: int, data: dict, session: Session = S):
    p = _apply(_get(session, Product, pid), data, exclude=("id", "key"))
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@api.post("/products")
def create_product(data: dict, session: Session = S):
    key = data.get("key") or ("custom_" + uuid.uuid4().hex[:8])
    p = _apply(Product(key=key, name=data["name"], kind=data.get("kind", "stimulant")), data, exclude=("id", "key"))
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@api.get("/soils")
def soils(session: Session = S):
    return session.exec(select(SoilProfile)).all()


@api.post("/soils")
def create_soil(data: dict, session: Session = S):
    s = _apply(SoilProfile(name=data["name"]), data)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@api.patch("/soils/{sid}")
def update_soil(sid: int, data: dict, session: Session = S):
    s = _apply(_get(session, SoilProfile, sid), data)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@api.get("/waters")
def waters(session: Session = S):
    return session.exec(select(WaterProfile)).all()


@api.patch("/waters/{wid}")
def update_water(wid: int, data: dict, session: Session = S):
    w = _apply(_get(session, WaterProfile, wid), data)
    session.add(w)
    session.commit()
    session.refresh(w)
    return w


@api.get("/strains")
def strains(session: Session = S):
    return session.exec(select(Strain)).all()


@api.post("/strains")
def create_strain(data: dict, session: Session = S):
    s = _apply(Strain(name=data["name"]), data)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@api.patch("/strains/{sid}")
def update_strain(sid: int, data: dict, session: Session = S):
    s = _apply(_get(session, Strain, sid), data)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@api.get("/schedules")
def schedules(session: Session = S):
    out = []
    for fs in session.exec(select(FeedingSchedule)).all():
        rows = session.exec(select(ScheduleEntry).where(ScheduleEntry.schedule_id == fs.id)).all()
        table: dict[str, dict] = {}
        for r in rows:
            table.setdefault(r.product_key, {})[r.stage] = r.dose_per_l
        out.append({**fs.model_dump(), "table": table})
    return out


# ------------------------------------------------------------------ Aufgaben

@api.get("/tasks")
def list_tasks(session: Session = S):
    return session.exec(select(Task).where(Task.active == True).order_by(Task.due_on)).all()  # noqa: E712


@api.post("/tasks")
def create_task(data: dict, session: Session = S):
    t = _apply(Task(title=data["title"], due_on=date.today()), data)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@api.post("/tasks/{tid}/done")
def task_done(tid: int, session: Session = S):
    t = _get(session, Task, tid)
    t.last_done_on = date.today()
    if t.interval_days:
        t.due_on = date.today() + timedelta(days=t.interval_days)
    else:
        t.active = False
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@api.patch("/tasks/{tid}")
def update_task(tid: int, data: dict, session: Session = S):
    t = _apply(_get(session, Task, tid), data)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@api.delete("/tasks/{tid}")
def delete_task(tid: int, session: Session = S):
    session.delete(_get(session, Task, tid))
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------------ Schädlinge

@api.get("/pests/catalog")
def pest_catalog():
    from .pest_data import CATEGORY_LABEL, PESTS
    return {"pests": PESTS, "categories": CATEGORY_LABEL}


def _case_dict(session: Session, c) -> dict:
    from .logic import pests
    p = pests.PEST.get(c.pest_key, pests.PEST["sonstiges"])
    phase, bw = services.case_phase(session, c)
    logs = session.exec(select(LogEntry).where(LogEntry.case_id == c.id).order_by(LogEntry.ts.desc())).all()
    tasks = session.exec(select(Task).where(Task.case_id == c.id, Task.active == True).order_by(Task.due_on)).all()  # noqa: E712
    plants = session.exec(select(Plant).where(Plant.run_id == c.run_id)).all()
    return {**c.model_dump(mode="json"), "pest": {k: p[k] for k in ("key", "name", "category", "signs", "causes", "prevention")},
            "phase": phase, "bloom_week": bw,
            "treatments": [pests.evaluate(t, phase, bw) for t in p["treatments"]],
            "logs": [_log_dict(session, l) for l in logs], "tasks": [t.model_dump(mode="json") for t in tasks],
            "plants": [{"id": pl.id, "name": pl.name} for pl in plants]}


@api.get("/pests/cases")
def pest_cases(run_id: Optional[int] = None, session: Session = S):
    from .models import PestCase
    q = select(PestCase)
    if run_id:
        q = q.where(PestCase.run_id == run_id)
    rows = session.exec(q.order_by(PestCase.status == "erledigt", PestCase.started_on.desc())).all()
    return [{**c.model_dump(mode="json"), "open_tasks": len(session.exec(select(Task).where(Task.case_id == c.id, Task.active == True)).all())}  # noqa: E712
            for c in rows]


@api.get("/pests/cases/{cid}")
def pest_case(cid: int, session: Session = S):
    from .models import PestCase
    return _case_dict(session, _get(session, PestCase, cid))


@api.post("/pests/cases")
def pest_case_create(data: dict, session: Session = S):
    from .logic import pests
    from .models import PestCase
    pest = pests.PEST.get(data.get("pest_key"), pests.PEST["sonstiges"])
    scope = data.get("scope") or ("zelt" if pest["default_scope"] == "zelt" else "pflanzen")
    c = PestCase(run_id=data["run_id"], pest_key=pest["key"], name=data.get("name") or pest["name"], scope=scope,
                 plant_ids=[int(x) for x in data.get("plant_ids") or []] if scope == "pflanzen" else [],
                 status=data.get("status") or "offen", severity=int(data.get("severity") or 1),
                 started_on=date.fromisoformat(data.get("started_on") or date.today().isoformat()), notes=data.get("notes", ""))
    session.add(c)
    session.commit()
    session.refresh(c)
    if data.get("attach_log_id"):
        l = _get(session, LogEntry, int(data["attach_log_id"]))
        l.case_id = c.id
        if scope == "zelt":
            l.plant_id = None
        session.add(l)
    elif data.get("text") or data.get("with_finding", True):
        session.add(LogEntry(run_id=c.run_id, plant_id=c.plant_ids[0] if len(c.plant_ids) == 1 else None, case_id=c.id,
                             type="pest", text=data.get("text") or f"{c.name} festgestellt", severity=c.severity))
    session.commit()
    return _case_dict(session, c)


@api.patch("/pests/cases/{cid}")
def pest_case_update(cid: int, data: dict, session: Session = S):
    from .models import PestCase
    c = _get(session, PestCase, cid)
    _apply(c, {k: v for k, v in data.items() if k in ("status", "scope", "plant_ids", "severity", "notes", "name")})
    if c.scope == "zelt":
        c.plant_ids = []
    if c.status == "erledigt":
        c.closed_on = c.closed_on or date.today()
        for t in session.exec(select(Task).where(Task.case_id == cid, Task.active == True)).all():  # noqa: E712
            t.active = False
            session.add(t)
    else:
        c.closed_on = None
    session.add(c)
    session.commit()
    return _case_dict(session, c)


@api.delete("/pests/cases/{cid}")
def pest_case_delete(cid: int, session: Session = S):
    from .models import PestCase
    c = _get(session, PestCase, cid)
    for t in session.exec(select(Task).where(Task.case_id == cid)).all():
        session.delete(t)
    for l in session.exec(select(LogEntry).where(LogEntry.case_id == cid)).all():
        _delete_log(session, l)
    session.delete(c)
    session.commit()
    return {"ok": True}


@api.post("/pests/cases/{cid}/finding")
def pest_finding(cid: int, data: dict, session: Session = S):
    from .models import PestCase
    c = _get(session, PestCase, cid)
    if data.get("severity"):
        c.severity = int(data["severity"])
        session.add(c)
    l = LogEntry(run_id=c.run_id, plant_id=c.plant_ids[0] if len(c.plant_ids or []) == 1 else None, case_id=c.id,
                 type="pest", text=data.get("text", ""), severity=c.severity)
    session.add(l)
    session.commit()
    session.refresh(l)
    return _log_dict(session, l)


@api.post("/pests/cases/{cid}/treatment")
def pest_treatment(cid: int, data: dict, session: Session = S):
    from .logic import pests
    from .models import PestCase
    c = _get(session, PestCase, cid)
    pest = pests.PEST.get(c.pest_key, pests.PEST["sonstiges"])
    tr = next((t for t in pest["treatments"] if t["key"] == data.get("treatment_key")), None)
    name = tr["name"] if tr else (data.get("name") or "Maßnahme")
    day = date.fromisoformat(data.get("date") or date.today().isoformat())
    l = LogEntry(run_id=c.run_id, plant_id=c.plant_ids[0] if len(c.plant_ids or []) == 1 else None, case_id=c.id,
                 type="treatment", ts=datetime.combine(day, datetime.now().time().replace(microsecond=0)),
                 text=f"{name}" + (f": {data['text']}" if data.get("text") else ""), tags=[tr["key"]] if tr else [])
    session.add(l)
    created = []
    if tr and tr.get("repeat") and data.get("plan_repeats", True):
        rep = tr["repeat"]
        for i in range(1, rep["times"]):
            t = Task(run_id=c.run_id, case_id=c.id, title=f"{c.name}: {name} – {i + 1}. Anwendung",
                     due_on=day + timedelta(days=rep["interval_days"] * i))
            session.add(t)
            created.append(t)
    if c.status == "offen":
        c.status = "behandlung"
        session.add(c)
    session.commit()
    session.refresh(l)
    return {"log": _log_dict(session, l), "follow_ups": [t.due_on.isoformat() for t in created]}


# ------------------------------------------------------------------ Living Soil

def _owned(session: Session) -> set:
    from .living_soil_data import OWNED_DEFAULT
    from .models import Setting
    s = session.get(Setting, "ls_owned")
    return set(s.value.get("keys", [])) if s else set(OWNED_DEFAULT)


def _ls_mode(session: Session) -> Optional[str]:
    from .models import Setting
    s = session.get(Setting, "ls_mode")
    return s.value.get("mode") if s else None


@api.get("/living-soil")
def ls_info(session: Session = S):
    from .living_soil_data import INGREDIENTS, RECIPES, ROLE_LABEL, TEAS
    mode = _ls_mode(session)
    vegan = mode == "vegan"
    return {"mode": mode,
            "ingredients": [i for i in INGREDIENTS if not (vegan and not i["vegan"])],
            "recipes": [r for r in RECIPES if not (vegan and not r["vegan"])],
            "teas": [t for t in TEAS if not (vegan and t.get("vegan") is False)],
            "roles": ROLE_LABEL, "owned": sorted(_owned(session))}


@api.put("/living-soil/mode")
def ls_set_mode(data: dict, session: Session = S):
    from .models import Setting
    mode = data.get("mode")
    if mode not in ("vegan", "alle"):
        raise HTTPException(400, "mode muss 'vegan' oder 'alle' sein")
    s = session.get(Setting, "ls_mode") or Setting(key="ls_mode")
    s.value = {"mode": mode}
    session.add(s)
    session.commit()
    return {"mode": mode}


@api.put("/living-soil/owned")
def ls_set_owned(data: dict, session: Session = S):
    from .models import Setting
    s = session.get(Setting, "ls_owned") or Setting(key="ls_owned")
    s.value = {"keys": sorted(set(data.get("keys", [])))}
    session.add(s)
    session.commit()
    return {"owned": s.value["keys"]}


@api.post("/living-soil/calc")
def ls_calc(data: dict, session: Session = S):
    from .logic import living_soil
    if data.get("recipe_key") not in living_soil.REC:
        raise HTTPException(404, "Rezept nicht gefunden")
    try:
        return living_soil.calculate(data["recipe_key"], float(data.get("volume_l") or 60), data.get("choices") or {},
                                     _owned(session), data.get("include_optional", True), _ls_mode(session) == "vegan")
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.get("/living-soil/batches")
def ls_batches(session: Session = S):
    from .models import SoilBatch
    return session.exec(select(SoilBatch).order_by(SoilBatch.started_on.desc())).all()


@api.post("/living-soil/batches")
def ls_create_batch(data: dict, session: Session = S):
    from .logic import living_soil
    from .models import SoilBatch
    try:
        calc = living_soil.calculate(data["recipe_key"], float(data.get("volume_l") or 60), data.get("choices") or {},
                                     _owned(session), data.get("include_optional", True), _ls_mode(session) == "vegan")
    except ValueError as e:
        raise HTTPException(400, str(e))
    started = date.fromisoformat(data.get("started_on") or date.today().isoformat())
    rest = calc["recipe"]["rest_days"]
    b = SoilBatch(name=data.get("name") or calc["recipe"]["name"], recipe_key=data["recipe_key"], volume_l=calc["volume_l"],
                  choices={x["role"]: x["key"] for x in calc["bulk"]}, calc=calc, started_on=started,
                  ready_on=started + timedelta(days=rest[0]), status="reift" if rest[1] > 0 else "fertig",
                  notes=data.get("notes", ""))
    session.add(b)
    session.commit()
    session.refresh(b)
    if rest[1] > 0:
        session.add_all([
            Task(batch_id=b.id, title=f"Ansatz „{b.name}“: Feuchte prüfen", interval_days=3, due_on=started + timedelta(days=3)),
            Task(batch_id=b.id, title=f"Ansatz „{b.name}“: wenden", interval_days=7, due_on=started + timedelta(days=7)),
            Task(batch_id=b.id, title=f"Ansatz „{b.name}“ ist voraussichtlich fertig – Geruch und Temperatur prüfen",
                 due_on=b.ready_on),
        ])
        session.commit()
        session.refresh(b)
    return b


@api.patch("/living-soil/batches/{bid}")
def ls_update_batch(bid: int, data: dict, session: Session = S):
    from .models import SoilBatch
    b = _apply(_get(session, SoilBatch, bid), data, exclude=("id", "calc", "recipe_key"))
    if b.status in ("fertig", "verwendet"):
        for t in session.exec(select(Task).where(Task.batch_id == bid, Task.active == True)).all():  # noqa: E712
            t.active = False
            session.add(t)
    session.add(b)
    session.commit()
    session.refresh(b)
    return b


@api.delete("/living-soil/batches/{bid}")
def ls_delete_batch(bid: int, session: Session = S):
    from .models import SoilBatch
    b = _get(session, SoilBatch, bid)
    for t in session.exec(select(Task).where(Task.batch_id == bid)).all():
        session.delete(t)
    session.delete(b)
    session.commit()
    return {"ok": True}


@api.post("/living-soil/batches/{bid}/soil")
def ls_batch_to_soil(bid: int, session: Session = S):
    """Legt aus dem Ansatz ein Erdprofil mit Düngelogik „Living Soil“ an."""
    from .models import SoilBatch
    b = _get(session, SoilBatch, bid)
    if b.soil_id:
        return session.get(SoilProfile, b.soil_id)
    comps = [{"name": x["name"], "pct": round(x["share"] * 100)} for x in b.calc.get("bulk", [])]
    soil = SoilProfile(name=f"Living Soil: {b.name}", schedule_type="living_soil", prefertilized_weeks=0,
                       worm_humus_pct=next((c["pct"] for c in comps if "Wurmhumus" in c["name"]), 0), components=comps,
                       notes=f"Angesetzt am {b.started_on:%d.%m.%Y} nach Rezept „{b.calc['recipe']['name']}“.")
    session.add(soil)
    session.commit()
    session.refresh(soil)
    b.soil_id = soil.id
    session.add(b)
    session.commit()
    session.refresh(soil)
    return soil


# ------------------------------------------------------------------ Keimung

@api.get("/germination")
def germination_list():
    from .germination_data import AFTER_PLANTING, GENERAL, METHODS
    return {"general": GENERAL, "after_planting": AFTER_PLANTING, "methods": METHODS}


# ------------------------------------------------------------------ Training

@api.get("/training")
def training_list(session: Session = S):
    return session.exec(select(TrainingTechnique).order_by(TrainingTechnique.category, TrainingTechnique.name)).all()


@api.get("/training/{key}")
def training_get(key: str, session: Session = S):
    t = session.exec(select(TrainingTechnique).where(TrainingTechnique.key == key)).first()
    if not t:
        raise HTTPException(404, "Technik nicht gefunden")
    return t


@api.patch("/training/{key}")
def training_update(key: str, data: dict, session: Session = S):
    t = training_get(key, session)
    allowed = {"my_notes"} if t.builtin else set(TrainingTechnique.model_fields) - {"id", "key", "builtin"}
    _apply(t, {k: v for k, v in data.items() if k in allowed})
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@api.post("/training")
def training_create(data: dict, session: Session = S):
    key = data.get("key") or ("eigen_" + uuid.uuid4().hex[:8])
    t = _apply(TrainingTechnique(key=key, name=data["name"], category=data.get("category", "lst"),
                                 stress=data.get("stress", "niedrig"), auto=data.get("auto", "bedingt"),
                                 photo=data.get("photo", "bedingt"), builtin=False), data, exclude=("id", "key", "builtin"))
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@api.delete("/training/{key}")
def training_delete(key: str, session: Session = S):
    t = training_get(key, session)
    if t.builtin:
        raise HTTPException(400, "Eingebaute Techniken können nicht gelöscht werden")
    session.delete(t)
    session.commit()
    return {"ok": True}


@api.get("/plants/{pid}/training")
def plant_training(pid: int, session: Session = S):
    plant = _get(session, Plant, pid)
    run = session.get(Run, plant.run_id)
    st = services.plant_status(session, plant, run, session.get(Setup, run.setup_id))
    return services.plant_training(session, plant, space_status=st["space"]["status"])


# ------------------------------------------------------------------ Export

@api.get("/export")
def export(session: Session = S):
    data: dict[str, Any] = {}
    for model in (Setup, Equipment, SensorMapping, SoilProfile, WaterProfile, Product, FeedingSchedule, ScheduleEntry,
                  Strain, LightCalibration, Run, Plant, LogEntry, Photo, Task, TrainingTechnique):
        data[model.__tablename__] = [o.model_dump(mode="json") for o in session.exec(select(model)).all()]
    return data
