import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from . import __version__
from .db import DATA_DIR, engine, init_db
from .logic import climate
from .models import SensorMapping
from .routes import api
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("grow")

FRONTEND = Path(os.environ.get("GROW_FRONTEND_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))


def options() -> dict:
    p = DATA_DIR / "options.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except json.JSONDecodeError:
        return {}


async def sample_job():
    with Session(engine) as s:
        setup_ids = {m.setup_id for m in s.exec(select(SensorMapping)).all()}
        for sid in setup_ids:
            try:
                await climate.sample(s, sid)
            except Exception as e:  # Sensorfehler dürfen die App nicht stoppen
                log.warning("Klima-Aufzeichnung Setup %s fehlgeschlagen: %s", sid, e)


def aggregate_job():
    with Session(engine) as s:
        n = climate.aggregate_old(s)
        if n:
            log.info("Klima: %s Stundenwerte verdichtet", n)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as s:
        if seed(s):
            log.info("Startdaten angelegt")
    sched = AsyncIOScheduler()
    interval = int(options().get("climate_interval_minutes", 10) or 10)
    sched.add_job(sample_job, "interval", minutes=interval, id="climate", next_run_time=None)
    sched.add_job(aggregate_job, "cron", hour=3, minute=17, id="aggregate")
    sched.start()
    sched.modify_job("climate", next_run_time=__import__("datetime").datetime.now())
    log.info("Grow-Tagebuch %s gestartet, Klima alle %s min", __version__, interval)
    yield
    sched.shutdown(wait=False)


app = FastAPI(title="Grow-Tagebuch", version=__version__, lifespan=lifespan)
app.include_router(api)


@app.get("/api/health")
def health():
    return {"ok": True, "version": __version__}


if (FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    f = FRONTEND / path
    if path and f.is_file():
        return FileResponse(f)
    index = FRONTEND / "index.html"
    if index.exists():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return {"msg": "Frontend nicht gebaut"}
