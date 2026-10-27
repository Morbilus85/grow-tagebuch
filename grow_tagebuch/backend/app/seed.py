"""Startdaten – werden nur in eine leere Datenbank geschrieben."""
from datetime import date, timedelta

from sqlmodel import Session, select

from .models import (
    Equipment,
    FeedingSchedule,
    LightCalibration,
    Product,
    Run,
    ScheduleEntry,
    SensorMapping,
    Setup,
    SoilProfile,
    Strain,
    Task,
    WaterProfile,
)

BIOBIZZ_URL = "https://www.biobizz.com/wp-content/uploads/2021/10/Nutrient-Schedule-DE-Microbes-2021.pdf"
STAGES = ["seedling", "veg"] + [f"bloom_{i}" for i in range(1, 9)]

# BioBizz Nutrient Schedule, ml/l (Microbes g/l). Spalten: Anzucht, Wachstum, Blüte W1–W8.
ALL_MIX = {
    "biobizz_root_juice": [4, 4, 2, 2, 0, 0, 0, 0, 0, 0],
    "biobizz_microbes": [0.4, 0.4, 0.2, 0.2, 0.4, 0.4, 0.4, 0.2, 0.2, 0.2],
    "biobizz_bio_grow": [2, 2, 3, 2, 2, 2, 2, 2, 2, 1],
    "biobizz_bio_bloom": [0, 0, 1, 2, 3, 3, 3, 4, 4, 4],
    "biobizz_top_max": [0, 0, 1, 2, 2, 3, 3, 4, 4, 4],
    "biobizz_bio_heaven": [2, 2, 2, 3, 4, 5, 5, 4, 4, 3],
    "biobizz_acti_vera": [2, 2, 3, 4, 5, 5, 3, 3, 2, 1],
}
LIGHT_MIX = {
    "biobizz_root_juice": [4, 4, 2, 2, 0, 0, 0, 0, 0, 0],
    "biobizz_microbes": [0.4, 0.4, 0.2, 0.2, 0.4, 0.4, 0.4, 0.2, 0.2, 0.2],
    "biobizz_bio_grow": [2, 2, 3, 4, 4, 4, 2, 2, 2, 1],
    "biobizz_bio_bloom": [0, 0, 2, 3, 3, 4, 4, 4, 3, 3],
    "biobizz_top_max": [0, 0, 1, 2, 2, 3, 3, 4, 4, 1],
    "biobizz_bio_heaven": [2, 2, 2, 3, 4, 5, 5, 3, 3, 2],
    "biobizz_acti_vera": [2, 2, 3, 4, 5, 5, 3, 3, 2, 1],
    "biobizz_alg_a_mic": [0, 2, 2, 2, 3, 3, 4, 4, 3, 2],
}

PRODUCTS = [
    # key, name, brand, kind, form, unit, application, min, max, group, in_stock, notes
    ("biobizz_root_juice", "Root-Juice", "BioBizz", "root", "fluessig", "ml", ["giessen"], 1, 4, "wurzel", True, ""),
    ("biobizz_bio_grow", "Bio-Grow", "BioBizz", "base", "fluessig", "ml", ["giessen"], 1, 4, "", True, "NK-Grunddünger, auch in der Blüte"),
    ("biobizz_bio_bloom", "Bio-Bloom", "BioBizz", "base", "fluessig", "ml", ["giessen"], 1, 4, "", True, "Blütedünger"),
    ("biobizz_top_max", "Top-Max", "BioBizz", "stimulant", "fluessig", "ml", ["giessen"], 1, 4, "", True, "Blütestimulator"),
    ("biobizz_bio_heaven", "Bio-Heaven", "BioBizz", "stimulant", "fluessig", "ml", ["giessen"], 2, 5, "", True, "Aminosäuren"),
    ("biobizz_acti_vera", "Acti-Vera", "BioBizz", "stimulant", "fluessig", "ml", ["giessen", "spray"], 2, 5, "aloe", True, ""),
    ("biobizz_calmag", "CalMag", "BioBizz", "calmag", "fluessig", "ml", ["giessen"], None, None, "", True, "Dosis laut Etikett eintragen"),
    ("biobizz_bio_down", "Bio-Down", "BioBizz", "ph", "fluessig", "ml", ["giessen"], None, None, "", True, "pH-Senker, nach Messung dosieren"),
    ("biobizz_worm_humus", "Worm-Humus", "BioBizz", "amendment", "fest", "l", ["einmischen", "topdress"], None, None, "", True, ""),
    ("biobizz_microbes", "Microbes", "BioBizz", "microbial", "pulver", "g", ["giessen"], None, None, "mikroben", False, "nicht im Inventar"),
    ("biobizz_alg_a_mic", "Alg-A-Mic", "BioBizz", "stimulant", "fluessig", "ml", ["giessen", "spray"], None, None, "", False, "nicht im Inventar"),
    ("biobizz_fish_mix", "Fish-Mix", "BioBizz", "base", "fluessig", "ml", ["giessen"], None, None, "", False, "nicht im Inventar; Alternative zu Bio-Grow"),
    ("dimikro_bodenhilfsstoff", "Bodenhilfsstoff (EM)", "DiMikro", "microbial", "fluessig", "ml", ["giessen"], None, None, "mikroben", True, "Dosis laut Etikett eintragen"),
    ("neemoel", "Neemöl", "", "plant_protection", "fluessig", "ml", ["spray"], None, None, "", True, "Nur Spray, nicht ab Vorblüte"),
    ("ackerschachtelhalm", "Ackerschachtelhalm-Konzentrat", "", "plant_protection", "fluessig", "ml", ["giessen", "spray"], None, None, "", True, "Dosis laut Etikett eintragen"),
    ("bio_backmalz", "Bio-Backmalz", "", "carbs", "pulver", "g", ["giessen"], None, None, "kohlenhydrate", True, ""),
    ("melasse", "Melasse", "", "carbs", "fluessig", "ml", ["giessen"], None, None, "kohlenhydrate", True, ""),
    ("rootmax", "Rootmax", "", "root", "fluessig", "ml", ["giessen"], None, None, "wurzel", True, "Dosis laut Etikett eintragen"),
    ("brennnesselpulver", "Brennnesselpulver", "", "amendment", "pulver", "g", ["giessen", "topdress"], None, None, "stickstoff", True, "stickstofflastig"),
    ("neem_cake", "Neem Cake", "", "amendment", "fest", "g", ["einmischen", "topdress"], None, None, "", True, ""),
    ("aloe_vera_puder", "Aloe-Vera-Puder", "", "stimulant", "pulver", "g", ["giessen", "spray"], None, None, "aloe", True, ""),
]

# Lichtmessung 27.10.2026, Ionframe EVO4, PAR-Meter, Mitte (A) + Rand (B–E)
LIGHT_CAL = [
    (30, 3, "A", 454.0), (30, 5, "A", 666.0), (30, 7, "A", 862.2), (30, 10, "A", 1180.2),
    (45, 3, "A", 314.8), (45, 5, "A", 462.0), (45, 7, "A", 598.0), (45, 10, "A", 816.8),
    (60, 3, "A", 230.2), (60, 5, "A", 337.5), (60, 7, "A", 437.2), (60, 10, "A", 598.2),
    (45, 7, "B", 398.7), (45, 7, "C", 315.2), (45, 7, "D", 348.4), (45, 7, "E", 392.7),
]

SENSORS = {
    "temp": "sensor.homegrow_probe_sensor_sonden_temperatur",
    "rh": "sensor.homegrow_probe_sensor_sonden_luftfeuchtigkeit",
    "vpd": "sensor.homegrow_probe_sensor_sonden_vpd",
    "light_level": "sensor.homegrow_port_2_aktuelle_leistung",
    "light_on": "binary_sensor.homegrow_port_2_zustand",
    "exhaust_level": "sensor.homegrow_port_1_aktuelle_leistung",
    "heater_switch": "switch.steckdose_growzelt_heizung",
    "heatmat_switch": "switch.steckdose_heizmatte",
    "room_temp": "sensor.sensor_display_grow_room_temperature",
    "room_rh": "sensor.sensor_display_grow_room_humidity",
}


def seed(session: Session) -> bool:
    if session.exec(select(Setup)).first():
        return False

    tent = Setup(name="Growzelt", kind="zelt", indoor=True, width_cm=90, depth_cm=90, height_cm=180, lamp_hang_cm=15)
    bed = Setup(name="Hochbeet Garten", kind="hochbeet", indoor=False, notes="ca. 100 l, Ost/Nordost")
    session.add_all([tent, bed])
    session.flush()

    session.add_all([
        Equipment(setup_id=tent.id, category="zelt", brand="AC Infinity", model="CLOUDLAB 733", specs={"masse": "90x90x180 cm", "material": "2000D Mylar"}),
        Equipment(setup_id=tent.id, category="licht", brand="AC Infinity", model="IONFRAME EVO4", specs={"watt": 300, "chip": "Samsung LM301H EVO", "stufen": "1–10", "controller_port": 2}),
        Equipment(setup_id=tent.id, category="abluft", brand="AC Infinity", model="CLOUDLINE PRO S6", specs={"durchmesser_mm": 150, "controller_port": 1}),
        Equipment(setup_id=tent.id, category="filter", brand="AC Infinity", model="Aktivkohlefilter 150 mm"),
        Equipment(setup_id=tent.id, category="umluft", brand="AC Infinity", model="CLOUDRAY S6"),
        Equipment(setup_id=tent.id, category="controller", brand="AC Infinity", model="CONTROLLER AI+"),
        Equipment(setup_id=tent.id, category="topf", brand="AC Infinity", model="Stofftopf 19 l", specs={"liter": 19, "anzahl": 5}),
        Equipment(setup_id=tent.id, category="heizmatte", model="Heizmatte", specs={"steckdose": SENSORS["heatmat_switch"]}),
        Equipment(setup_id=tent.id, category="heizung", model="Zusatzheizung", specs={"steckdose": SENSORS["heater_switch"]}),
    ])
    for role, ent in SENSORS.items():
        session.add(SensorMapping(setup_id=tent.id, role=role, entity_id=ent))

    for d, lvl, pt, val in LIGHT_CAL:
        session.add(LightCalibration(setup_id=tent.id, measured_on=date(2026, 10, 27), distance_cm=d, level=lvl, point=pt, ppfd=val))

    soil = SoilProfile(
        name="Floragard Grow Mix Organic + Wurmhumus",
        schedule_type="all_mix",
        prefertilized_weeks=4,
        worm_humus_pct=15,
        components=[
            {"name": "Floragard Professional Grow Mix Organic", "pct": 85},
            {"name": "BioBizz Worm-Humus", "pct": 15},
        ],
        notes="Erde laut Hersteller bis zu 4 Wochen vorgedüngt; Wurmhumus 10–20 %",
    )
    water = WaterProfile(
        name="Essen Leitungswasser (Q4/2025)", source="leitung", ec=0.47, ph=7.9,
        ca_mg_l=39, mg_mg_l=7.6, na_mg_l=39, k_mg_l=4.4, cl_mg_l=52, so4_mg_l=38, no3_mg_l=10.8,
        acid_capacity_mmol=2.08, hardness_dh=7.2, carbonate_hardness_dh=5.8, measured_on=date(2025, 12, 31),
        source_url="https://www.stadtwerke-essen.de/fileadmin/user_upload/pdf/netz/2025-4._Quartal_00-0350_SWE.pdf",
    )
    session.add_all([soil, water])

    for key, name, brand, kind, form, unit, app, mn, mx, grp, stock, notes in PRODUCTS:
        session.add(Product(key=key, name=name, brand=brand, kind=kind, form=form, unit=unit, application=app,
                            label_dose_min=mn, label_dose_max=mx, effect_group=grp, in_stock=stock, notes=notes))

    schedules = {}
    for stype, table in (("all_mix", ALL_MIX), ("light_mix", LIGHT_MIX)):
        fs = FeedingSchedule(brand="BioBizz", name=f"BioBizz {'All-Mix' if stype == 'all_mix' else 'Light-Mix/Coco-Mix'}",
                             schedule_type=stype, version="2021/2024", source_url=BIOBIZZ_URL, retrieved_on=date(2026, 10, 27))
        session.add(fs)
        session.flush()
        schedules[stype] = fs
        for key, doses in table.items():
            for stage, dose in zip(STAGES, doses):
                if dose:
                    session.add(ScheduleEntry(schedule_id=fs.id, stage=stage, product_key=key, dose_per_l=dose))

    strain = Strain(name="Strawberry Cough Auto", breeder="Zamnesia Seeds", auto=True, seed_to_harvest_days=74,
                    max_height_cm=120, genetics="Strawberry Fields × Haze × Ruderalis", notes="Breeder: 10–11 Wochen Samen bis Ernte")
    session.add(strain)
    session.flush()

    run = Run(name="Strawberry Cough Auto – Herbst 2026", setup_id=tent.id, soil_id=soil.id, water_id=water.id,
              schedule_id=schedules["all_mix"].id, start_date=date(2026, 10, 26), light_hours=20, light_level=3,
              lamp_distance_cm=60, notes="Samen am 26.10.2026 in Wasser + H2O2 eingeweicht")
    session.add(run)
    session.flush()

    today = date.today()
    session.add_all([
        Task(run_id=run.id, title="pH-Meter kalibrieren", interval_days=14, due_on=today),
        Task(run_id=run.id, title="Gelbtafeln prüfen", interval_days=7, due_on=today + timedelta(days=7)),
        Task(run_id=run.id, title="Töpfe eine Position weiterdrehen", interval_days=7, due_on=today + timedelta(days=7)),
    ])
    session.commit()
    return True
