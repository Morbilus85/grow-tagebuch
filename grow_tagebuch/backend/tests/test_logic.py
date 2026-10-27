import os
import tempfile
from datetime import date, datetime, timedelta
from types import SimpleNamespace as NS

os.environ.setdefault("GROW_DATA_DIR", tempfile.mkdtemp())

from app.logic import climate, feeding, light, phases, space  # noqa: E402
from app.seed import ALL_MIX, LIGHT_CAL, PRODUCTS, STAGES  # noqa: E402

STRAIN = NS(auto=True, seed_to_harvest_days=74, flowering_days=None)


def plant(**kw):
    base = dict(harvested_on=None, status="aktiv", sprouted_on=None, planted_on=None, soaked_on=None,
                preflower_on=None, flip_on=None)
    base.update(kw)
    return NS(**base)


# ---------------------------------------------------------------- Phasen

def test_phases_before_sprout():
    assert phases.compute(plant(soaked_on=date(2026, 10, 26)), STRAIN, date(2026, 10, 27)).phase == "einweichen"
    assert phases.compute(plant(planted_on=date(2026, 10, 28)), STRAIN, date(2026, 10, 29)).phase == "keimung"


def test_auto_timeline():
    s = date(2026, 11, 1)
    p = plant(sprouted_on=s)
    assert phases.compute(p, STRAIN, s).phase == "seedling"
    assert phases.compute(p, STRAIN, s).day == 1
    assert phases.compute(p, STRAIN, s + timedelta(days=20)).phase == "veg"
    info = phases.compute(p, STRAIN, s + timedelta(days=30))
    assert info.phase == "bloom" and info.bloom_week == 1 and info.schedule_stage == "bloom_1"
    assert info.preflower_estimated
    assert phases.compute(p, STRAIN, s + timedelta(days=70)).phase == "flush"
    assert phases.compute(p, STRAIN, s + timedelta(days=80)).phase == "harvest"


def test_auto_bloom_columns_cover_schedule():
    s = date(2026, 11, 1)
    p = plant(sprouted_on=s)
    cols = {phases.compute(p, STRAIN, s + timedelta(days=d)).schedule_stage for d in range(25, 67)}
    assert "bloom_1" in cols and "bloom_8" in cols


def test_confirmed_preflower_anchors_bloom():
    s = date(2026, 11, 1)
    p = plant(sprouted_on=s, preflower_on=s + timedelta(days=21))
    info = phases.compute(p, STRAIN, s + timedelta(days=22))
    assert info.phase == "bloom" and not info.preflower_estimated


# ---------------------------------------------------------------- Licht

def _model():
    return light.LightModel([NS(distance_cm=d, level=l, point=pt, ppfd=v) for d, l, pt, v in LIGHT_CAL])


def test_light_reproduces_measurements():
    m = _model()
    for d, l, pt, v in LIGHT_CAL:
        if pt == "A":
            assert abs(m.ppfd(l, d) - v) / v < 0.05, (d, l, m.ppfd(l, d), v)


def test_light_interpolation_monotonic():
    m = _model()
    assert m.ppfd(5, 30) > m.ppfd(5, 40) > m.ppfd(5, 50) > m.ppfd(5, 60)
    assert m.ppfd(3, 45) < m.ppfd(5, 45) < m.ppfd(7, 45)


def test_light_seedling_recommendation():
    m = _model()
    rec = m.recommend("seedling", 20)
    assert rec and all(200 <= r["ppfd"] <= 300 and r["dli"] <= 20 for r in rec)
    a = light.assess(m, "bloom", 10, 30, 20)
    assert a["status"] == "zu_hoch"  # 1180 PPFD bei 20 h = DLI 85


def test_edge_factor():
    assert 0.55 <= _model().edge_factor <= 0.65


# ---------------------------------------------------------------- Düngung

PRODS = {k: NS(key=k, name=n, brand=b, kind=kind, unit=u, label_dose_min=mn, label_dose_max=mx, effect_group=g,
               in_stock=st) for k, n, b, kind, f, u, app, mn, mx, g, st, notes in PRODUCTS}
SOIL = NS(prefertilized_weeks=4, schedule_type="all_mix", worm_humus_pct=15)
WATER = NS(ec=0.47, ph=7.9, mg_mg_l=7.6)


def sched(stage):
    i = STAGES.index(stage)
    return {k: v[i] for k, v in ALL_MIX.items() if v[i]}


def ctx(stage, phase, weeks, bloom_week=None, logs=None, factor=1.0, mg=False):
    return feeding.PlantCtx(1, "P1", stage, phase, bloom_week, phase in ("bloom", "flush"), weeks,
                            factor, mg, logs or [])


def keys(r):
    return {i["key"] for i in r["items"]}


def test_seedling_only_root():
    r = feeding.build_recipe([ctx("seedling", "seedling", 1)], {1: 0.3}, sched("seedling"), PRODS, SOIL, WATER)
    assert keys(r) == {"biobizz_root_juice"}


def test_prefertilized_blocks_base():
    r = feeding.build_recipe([ctx("veg", "veg", 3)], {1: 1}, sched("veg"), PRODS, SOIL, WATER)
    assert "biobizz_bio_grow" not in keys(r)
    assert any(s["name"] == "Bio-Grow" for s in r["skipped"])
    heaven = next(i for i in r["items"] if i["key"] == "biobizz_bio_heaven")
    assert heaven["per_l"] == 1.0  # halbe Schemadosis


def test_ramp_after_prefert():
    r = feeding.build_recipe([ctx("bloom_2", "bloom", 5.2, 2)], {1: 2}, sched("bloom_2"), PRODS, SOIL, WATER)
    grow = next(i for i in r["items"] if i["key"] == "biobizz_bio_grow")
    assert r["factor"] == 0.5 and grow["per_l"] == 1.0 and grow["total"] == 2.0


def test_never_above_schedule():
    for w in (6, 8, 12):
        r = feeding.build_recipe([ctx("bloom_6", "bloom", w, 6, factor=1.5)], {1: 1}, sched("bloom_6"), PRODS, SOIL, WATER)
        for it in r["items"]:
            s = sched("bloom_6").get(it["key"])
            if s and it["per_l"] is not None:
                assert it["per_l"] <= s


def test_microbes_replaced_by_dimikro():
    r = feeding.build_recipe([ctx("veg", "veg", 8)], {1: 1}, sched("veg"), PRODS, SOIL, WATER)
    assert "dimikro_bodenhilfsstoff" in keys(r)


def test_calmag_from_bloom_only():
    r = feeding.build_recipe([ctx("veg", "veg", 8)], {1: 1}, sched("veg"), PRODS, SOIL, WATER)
    assert "biobizz_calmag" not in keys(r)
    r = feeding.build_recipe([ctx("bloom_3", "bloom", 8, 3)], {1: 1}, sched("bloom_3"), PRODS, SOIL, WATER)
    assert "biobizz_calmag" in keys(r)
    r = feeding.build_recipe([ctx("veg", "veg", 8, mg=True)], {1: 1}, sched("veg"), PRODS, SOIL, WATER)
    assert "biobizz_calmag" in keys(r)


def test_topdress_reduces():
    logs = [NS(type="top_dress", ts=datetime.now() - timedelta(days=3), products=[], ph_down_ml_per_l=None)]
    r = feeding.build_recipe([ctx("bloom_4", "bloom", 10, 4, logs)], {1: 1}, sched("bloom_4"), PRODS, SOIL, WATER)
    assert r["factor"] == 0.75


def test_flush_water_only():
    r = feeding.build_recipe([ctx("flush", "flush", 10)], {1: 1}, {}, PRODS, SOIL, WATER)
    assert r["items"] == []


def test_rules_neem_spray_and_duplicates():
    logs = [NS(type="feeding", ts=datetime.now() - timedelta(days=2), ph_down_ml_per_l=0.2,
               products=[{"product_key": "rootmax"}])]
    r = feeding.build_recipe([ctx("bloom_1", "bloom", 6, 1, logs)], {1: 1}, sched("bloom_1"), PRODS, SOIL, WATER,
                             extras=[{"product_key": "neemoel", "per_l": 2, "application": "spray"},
                                     {"product_key": "melasse", "per_l": 1}])
    assert any("Neemöl" in b for b in r["blocks"])
    assert any("wurzel" in w for w in r["warnings"])
    assert r["ph"]["bio_down_ml_per_l"] == 0.2


def test_carbs_warn_in_veg_and_nettle_in_bloom():
    r = feeding.build_recipe([ctx("veg", "veg", 8)], {1: 1}, sched("veg"), PRODS, SOIL, WATER,
                             extras=[{"product_key": "melasse", "per_l": 1}])
    assert any("Kohlenhydrate" in w for w in r["warnings"])
    r = feeding.build_recipe([ctx("bloom_3", "bloom", 8, 3)], {1: 1}, sched("bloom_3"), PRODS, SOIL, WATER,
                             extras=[{"product_key": "brennnesselpulver", "per_l": 1}])
    assert any("Brennnessel" in w for w in r["warnings"])


# ---------------------------------------------------------------- Klima & Platz

def test_vpd():
    assert climate.vpd_air(25, 60) == 1.27
    assert climate.vpd_leaf(25, 60) < climate.vpd_air(25, 60)
    assert climate.rate(1.0, (0.8, 1.2)) == "ok"


def test_space_warning():
    h = [(date(2026, 11, 20), 40.0), (date(2026, 11, 25), 55.0)]
    r = space.assess(180, 15, 30, h, 45, True, 4, 120)
    assert r["max_distance_cm"] == 80 and r["growth_cm_per_day"] == 3.0
    assert r["days_until_tight"] == 11
    r = space.assess(180, 15, 30, [(date(2026, 12, 1), 115.0)], 45, True, 7, 120)
    assert r["status"] == "kritisch"


# ---------------------------------------------------------------- Training

from app.logic import training  # noqa: E402
from app.training_data import TECHNIQUES  # noqa: E402

TECH = {t["key"]: NS(**t) for t in TECHNIQUES}


def ev(key, **kw):
    base = dict(auto=True, phase="veg", day=20, bloom_week=None, nodes=5, last_stress=None)
    base.update(kw)
    return training.evaluate(TECH[key], today=date(2026, 11, 20), **base)


def test_training_auto_rules():
    assert ev("mainlining")["status"] == "nicht_empfohlen"
    assert ev("lst")["status"] == "jetzt"
    assert ev("lst", day=10, phase="seedling")["status"] == "bald"
    assert ev("topping", nodes=3)["status"] == "bald"
    assert ev("topping", day=30)["status"] == "vorbei"
    assert ev("topping", auto=False, day=40)["status"] == "jetzt"
    assert ev("schwazzing", auto=False, phase="bloom", bloom_week=1)["status"] == "jetzt"
    assert ev("supercropping", phase="bloom", bloom_week=4, day=50)["status"] == "vorbei"


def test_training_recovery_and_height():
    r = ev("fim", last_stress=(date(2026, 11, 18), 7, "Toppen"))
    assert r["status"] == "warten"
    assert ev("lst", last_stress=(date(2026, 11, 18), 7, "Toppen"))["status"] == "jetzt"
    assert ev("lst", space_status="knapp")["priority"]


def test_training_rank():
    res = training.rank([ev(k) for k in TECH])
    assert res[0]["status"] == "jetzt" and res[-1]["status"] == "nicht_empfohlen"


def test_germination_timeline():
    from datetime import datetime as dt
    from app import services
    p = NS(sprouted_on=None, harvested_on=None, planted_on=None, soaked_on=date(2026, 10, 26),
           soaked_at=dt(2026, 10, 26, 18, 0), germ_method="h2o2")
    g = services.germination(p, dt(2026, 10, 27, 8, 0))
    assert g["stage"] == "einweichen" and "Nachsehen" in g["hint"] and g["next_in_hours"] == 10
    p.planted_on = date(2026, 10, 27)
    g = services.germination(p, dt(2026, 10, 30, 8, 0))
    assert g["stage"] == "in_erde" and "2–5 Tage" in g["hint"]


# ---------------------------------------------------------------- Living Soil

from app.logic import living_soil  # noqa: E402


def test_ls_calc_diy():
    r = living_soil.calculate("vegan_diy", 60, {"basis": "torf_ungeduengt"}, {"neem_cake", "dolomitkalk"})
    assert sum(b["amount"] for b in r["bulk"]) == 60
    neem = next(a for a in r["amendments"] if a["key"] == "neem_cake")
    assert neem["amount"] == 240 and neem["owned"]
    assert any(a["key"] == "dolomitkalk" for a in r["amendments"])
    r2 = living_soil.calculate("vegan_diy", 60, {"basis": "kokos"})
    assert not any(a["key"] == "dolomitkalk" for a in r2["amendments"])
    assert any(s["name"].startswith("Kelpmehl") for s in r["shopping"])


def test_ls_allinone_dose():
    r = living_soil.calculate("allinone_monster_bud", 20)
    mb = next(a for a in r["amendments"] if a["key"] == "monster_bud_ls")
    assert mb["amount"] == 220


def test_feeding_living_soil():
    soil = NS(prefertilized_weeks=0, schedule_type="living_soil", worm_humus_pct=30)
    r = feeding.build_recipe([ctx("veg", "veg", 3)], {1: 1}, sched("veg"), PRODS, soil, WATER,
                             extras=[{"product_key": "biobizz_bio_grow", "per_l": 2}])
    assert r["living_soil"] and not any(i["source"] == "schema" for i in r["items"])
    assert any("Grunddünger" in w for w in r["warnings"])
    assert any(s["key"] == "wurmhumustee" for s in r["suggestions"])
