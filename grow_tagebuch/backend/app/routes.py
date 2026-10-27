"""REST-API (alle Pfade relativ, damit sie hinter HA-Ingress funktionieren)."""
from __future__ import annotations

import io
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
        })
    return {"date": date.today().isoformat(), "runs": out, "legal": services.legal_status(session)}


# ------------------------------------------------------------------ Runs & Pflanzen

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
    run = _apply(Run(name=data.get("name", "Neuer Run"), setup_id=data["setup_id"], start_date=date.today()), data)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@api.patch("/runs/{rid}")
def update_run(rid: int, data: dict, session: Session = S):
    run = _apply(_get(session, Run, rid), data)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


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
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    except Exception:
        raise HTTPException(400, "Bild konnte nicht gelesen werden")
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
        l = LogEntry(run_id=req.run_id, plant_id=pl["id"], type="feeding" if items else "watering", volume_l=vol,
                     ph_in=req.ph_in, ec_in=req.ec_in, ph_down_ml_per_l=ph_down, products=products,
                     text=req.text, tags=[req.recipe.get("stage") or ""])
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
