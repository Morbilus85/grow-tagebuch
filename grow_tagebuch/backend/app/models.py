"""Datenmodell Grow-Tagebuch (SQLModel / SQLite)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


# ---------------------------------------------------------------- Stammdaten

class Setup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    kind: str = "zelt"  # zelt | hochbeet | freiland
    indoor: bool = True
    width_cm: Optional[int] = None
    depth_cm: Optional[int] = None
    height_cm: Optional[int] = None
    lamp_hang_cm: int = 15  # Aufhängung + Lampenkörper, geht von der Höhe ab
    notes: str = ""


class Equipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    setup_id: int = Field(foreign_key="setup.id")
    category: str  # zelt, licht, abluft, filter, umluft, controller, heizmatte, heizung, topf, messgeraet, sonstiges
    brand: str = ""
    model: str = ""
    specs: dict = Field(default_factory=dict, sa_column=Column(JSON))
    notes: str = ""


class SensorMapping(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    setup_id: int = Field(foreign_key="setup.id")
    role: str  # temp, rh, vpd, light_level, light_on, exhaust_level, heater_switch, heatmat_switch, room_temp, room_rh
    entity_id: str


class SoilProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    schedule_type: str = "all_mix"  # all_mix (vorgedüngt) | light_mix
    prefertilized_weeks: int = 4
    worm_humus_pct: int = 0
    components: list = Field(default_factory=list, sa_column=Column(JSON))
    notes: str = ""


class WaterProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    source: str = "leitung"
    ec: Optional[float] = None
    ph: Optional[float] = None
    ca_mg_l: Optional[float] = None
    mg_mg_l: Optional[float] = None
    na_mg_l: Optional[float] = None
    k_mg_l: Optional[float] = None
    cl_mg_l: Optional[float] = None
    so4_mg_l: Optional[float] = None
    no3_mg_l: Optional[float] = None
    acid_capacity_mmol: Optional[float] = None
    hardness_dh: Optional[float] = None
    carbonate_hardness_dh: Optional[float] = None
    measured_on: Optional[date] = None
    source_url: str = ""


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)  # z. B. biobizz_bio_grow
    name: str
    brand: str = ""
    kind: str  # base, stimulant, root, microbial, carbs, amendment, plant_protection, ph, calmag
    form: str = "fluessig"  # fluessig | pulver | fest
    unit: str = "ml"  # ml | g | Tropfen
    application: list = Field(default_factory=list, sa_column=Column(JSON))  # giessen, spray, einmischen, topdress
    label_dose_min: Optional[float] = None  # pro Liter Gießwasser
    label_dose_max: Optional[float] = None
    effect_group: str = ""  # Doppelungswarnung
    in_stock: bool = True
    notes: str = ""


class FeedingSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    brand: str
    name: str
    schedule_type: str  # all_mix | light_mix
    version: str = ""
    source_url: str = ""
    retrieved_on: Optional[date] = None


class ScheduleEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    schedule_id: int = Field(foreign_key="feedingschedule.id")
    stage: str  # seedling, veg, bloom_1..bloom_8
    product_key: str
    dose_per_l: float


class Strain(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    breeder: str = ""
    auto: bool = True
    seed_to_harvest_days: Optional[int] = None  # Autos
    flowering_days: Optional[int] = None  # Photos
    max_height_cm: Optional[int] = None
    genetics: str = ""
    notes: str = ""


class LightCalibration(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    setup_id: int = Field(foreign_key="setup.id")
    measured_on: date
    distance_cm: int
    level: int
    point: str = "A"  # A = Mitte, B-E = Rand
    ppfd: float


# ---------------------------------------------------------------- Runs

class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    setup_id: int = Field(foreign_key="setup.id")
    soil_id: Optional[int] = Field(default=None, foreign_key="soilprofile.id")
    water_id: Optional[int] = Field(default=None, foreign_key="waterprofile.id")
    schedule_id: Optional[int] = Field(default=None, foreign_key="feedingschedule.id")
    start_date: date
    status: str = "aktiv"  # geplant, aktiv, ernte, trocknung, curing, abgeschlossen
    light_hours: float = 20
    light_on_time: str = "06:00"
    light_level: Optional[int] = None
    lamp_distance_cm: Optional[int] = None  # Lampe -> Pflanzenspitze (bzw. Erde bei Keimling)
    notes: str = ""


class Plant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    strain_id: Optional[int] = Field(default=None, foreign_key="strain.id")
    name: str
    pot_l: Optional[float] = None
    pot_height_cm: int = 30
    soaked_on: Optional[date] = None
    planted_on: Optional[date] = None
    sprouted_on: Optional[date] = None
    preflower_on: Optional[date] = None  # bestätigt
    flip_on: Optional[date] = None  # Photos: Umstellung 12/12
    harvested_on: Optional[date] = None
    status: str = "aktiv"  # aktiv, geerntet, eingegangen
    feed_factor: float = 1.0  # manueller Stärkefaktor (wirkt auf das Schema)
    mg_deficiency_flag: bool = False
    notes: str = ""


class LogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plant_id: Optional[int] = Field(default=None, foreign_key="plant.id", index=True)
    run_id: int = Field(foreign_key="run.id", index=True)
    ts: datetime = Field(default_factory=now, index=True)
    type: str  # watering, feeding, foliar, top_dress, training, defoliation, observation, problem, pest, measurement, phase, harvest, note
    text: str = ""
    tags: list = Field(default_factory=list, sa_column=Column(JSON))
    # Gießen
    volume_l: Optional[float] = None
    ph_in: Optional[float] = None
    ec_in: Optional[float] = None
    runoff_l: Optional[float] = None
    ph_runoff: Optional[float] = None
    ec_runoff: Optional[float] = None
    pot_weight_kg: Optional[float] = None
    ph_down_ml_per_l: Optional[float] = None
    # Messung
    height_cm: Optional[float] = None
    lamp_distance_cm: Optional[float] = None
    nodes: Optional[int] = None  # Anzahl Nodien am Haupttrieb
    # Training
    technique_key: Optional[str] = None
    # Produkte: [{product_key, amount, unit, per_l, application}]
    products: list = Field(default_factory=list, sa_column=Column(JSON))
    # Schädlinge / Probleme
    severity: Optional[int] = None  # 1-3


class Photo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    log_id: int = Field(foreign_key="logentry.id", index=True)
    filename: str
    taken_at: datetime = Field(default_factory=now)
    width: Optional[int] = None
    height: Optional[int] = None


class ClimateSample(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    setup_id: int = Field(foreign_key="setup.id", index=True)
    ts: datetime = Field(index=True)
    temp: Optional[float] = None
    rh: Optional[float] = None
    vpd: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    rh_min: Optional[float] = None
    rh_max: Optional[float] = None
    light_level: Optional[float] = None
    heater_on: Optional[bool] = None
    heatmat_on: Optional[bool] = None
    aggregated: bool = False


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: Optional[int] = Field(default=None, foreign_key="run.id")
    title: str
    interval_days: Optional[int] = None  # None = einmalig
    due_on: date
    last_done_on: Optional[date] = None
    active: bool = True
    notes: str = ""


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: dict = Field(default_factory=dict, sa_column=Column(JSON))


class TrainingTechnique(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    name: str
    aka: str = ""
    category: str  # lst | hst | schnitt | methode
    stress: str  # sehr_niedrig | niedrig | mittel | hoch
    auto: str  # empfohlen | bedingt | abraten
    photo: str  # empfohlen | bedingt | abraten
    goal: str = ""
    summary: str = ""
    when: str = ""
    auto_note: str = ""
    steps: list = Field(default_factory=list, sa_column=Column(JSON))
    mistakes: list = Field(default_factory=list, sa_column=Column(JSON))
    tools: list = Field(default_factory=list, sa_column=Column(JSON))
    combines_with: list = Field(default_factory=list, sa_column=Column(JSON))
    window: dict = Field(default_factory=dict, sa_column=Column(JSON))  # Regeln für die Bewertung
    recovery_days: int = 0
    height_control: bool = False
    builtin: bool = True
    my_notes: str = ""
