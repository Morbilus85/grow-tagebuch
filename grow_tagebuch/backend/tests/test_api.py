import io
import os
import tempfile

os.environ["GROW_DATA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


def test_flow():
    with TestClient(app) as c:
        run = c.get("/api/runs").json()[0]
        strain = c.get("/api/strains").json()[0]
        p1 = c.post("/api/plants", json={"run_id": run["id"], "name": "SC 1", "strain_id": strain["id"], "pot_l": 19,
                                          "soaked_on": "2026-10-26", "planted_on": "2026-10-28",
                                          "sprouted_on": "2026-10-30"}).json()
        p2 = c.post("/api/plants", json={"run_id": run["id"], "name": "SC 2", "strain_id": strain["id"],
                                          "planted_on": "2026-10-28", "sprouted_on": "2026-10-30"}).json()
        today = c.get("/api/today").json()
        assert len(today["runs"][0]["plants"]) == 2

        rec = c.post("/api/feeding/recipe", json={"run_id": run["id"], "volumes": {p1["id"]: 0.3, p2["id"]: 0.2}}).json()
        assert len(rec) == 1 and rec[0]["total_l"] == 0.5
        r = c.post("/api/feeding/confirm", json={"run_id": run["id"], "recipe": rec[0], "ph_in": 6.4,
                                                 "ph_down_ml_total": 0.1}).json()
        assert r["created"] == 2
        logs = c.get(f"/api/logs?plant_id={p1['id']}").json()
        assert logs[0]["volume_l"] == 0.3 and logs[0]["ph_down_ml_per_l"] == 0.2

        # Messung + Foto + Bearbeiten + Löschen
        m = c.post("/api/logs", json={"plant_id": p1["id"], "type": "measurement", "height_cm": 4}).json()
        buf = io.BytesIO()
        Image.new("RGB", (3000, 2000), (20, 120, 20)).save(buf, "JPEG")
        ph = c.post(f"/api/logs/{m['id']}/photos", files={"file": ("a.jpg", buf.getvalue(), "image/jpeg")}).json()
        assert ph["width"] == 2560
        assert c.get(f"/api/photos/{ph['id']}?thumb=1").status_code == 200
        assert c.patch(f"/api/logs/{m['id']}", json={"height_cm": 5}).json()["height_cm"] == 5
        assert c.delete(f"/api/logs/{m['id']}").json()["ok"]

        assert c.get("/api/light/1").json()["calibrated"]
        assert c.get("/api/schedules").json()[0]["table"]["biobizz_bio_grow"]["veg"] == 2
        t = c.get("/api/tasks").json()[0]
        assert c.post(f"/api/tasks/{t['id']}/done").json()["last_done_on"]
        assert "logentry" in c.get("/api/export").json()


def test_household_limit():
    with TestClient(app) as c:
        assert c.put("/api/household", json={"adults": 1}).json()["plant_limit"] == 3
        run = c.get("/api/runs").json()[0]
        before = c.get("/api/household").json()["living_plants"]
        last = None
        for i in range(4 - before):
            last = c.post("/api/plants", json={"run_id": run["id"], "name": f"L{i}", "planted_on": "2026-10-27"}).json()
        assert "warning" in last
        assert c.put("/api/household", json={"adults": 3}).json()["status"] == "ok"


def test_living_soil_batch():
    with TestClient(app) as c:
        b = c.post("/api/living-soil/batches", json={"recipe_key": "vegan_diy", "volume_l": 66}).json()
        assert b["id"] and b["status"] == "reift" and b["calc"]["bulk"]
        assert any("Ansatz" in t["title"] for t in c.get("/api/tasks").json())
        soil = c.post(f"/api/living-soil/batches/{b['id']}/soil").json()
        assert soil["schedule_type"] == "living_soil"
        c.patch(f"/api/living-soil/batches/{b['id']}", json={"status": "fertig"})
        assert not any("Ansatz" in t["title"] for t in c.get("/api/tasks").json())


def test_living_soil_mode():
    with TestClient(app) as c:
        assert c.get("/api/living-soil").json()["mode"] is None
        c.put("/api/living-soil/mode", json={"mode": "vegan"})
        d = c.get("/api/living-soil").json()
        assert all(r["vegan"] for r in d["recipes"]) and all(i["vegan"] for i in d["ingredients"])
        assert c.post("/api/living-soil/calc", json={"recipe_key": "classic_diy"}).status_code == 400
        c.put("/api/living-soil/mode", json={"mode": "alle"})
        assert any(not r["vegan"] for r in c.get("/api/living-soil").json()["recipes"])


def test_pest_cases():
    with TestClient(app) as c:
        run = c.get("/api/runs").json()[0]
        plants = c.get(f"/api/runs/{run['id']}").json()["plants"]
        pid = plants[0]["id"]
        log = c.post("/api/logs", json={"plant_id": pid, "type": "pest", "text": "Mücken"}).json()
        case = c.post("/api/pests/cases", json={"run_id": run["id"], "pest_key": "trauermuecken", "attach_log_id": log["id"]}).json()
        assert case["scope"] == "zelt" and case["logs"][0]["plant_id"] is None
        nem = next(t for t in case["treatments"] if t["key"] == "nematoden_sf")
        assert nem["allowed"]
        r = c.post(f"/api/pests/cases/{case['id']}/treatment", json={"treatment_key": "nematoden_sf"}).json()
        assert len(r["follow_ups"]) == 1
        case = c.get(f"/api/pests/cases/{case['id']}").json()
        assert case["status"] == "behandlung" and case["tasks"]
        assert any(x["id"] == case["id"] for x in c.get("/api/today").json()["runs"][0]["cases"])
        assert c.get(f"/api/plants/{pid}").json()["cases"]
        m = c.post("/api/pests/cases", json={"run_id": run["id"], "pest_key": "mehltau", "plant_ids": [pid]}).json()
        assert m["scope"] == "pflanzen" and m["plant_ids"] == [pid]
        done = c.patch(f"/api/pests/cases/{case['id']}", json={"status": "erledigt"}).json()
        assert done["closed_on"] and not done["tasks"]


def test_abort_plant_and_restart_run():
    with TestClient(app) as c:
        run = c.get("/api/today").json()["runs"][0]["run"]
        p = c.post("/api/plants", json={"run_id": run["id"], "name": "Abbruch", "planted_on": "2026-10-27"}).json()
        case = c.post("/api/pests/cases", json={"run_id": run["id"], "pest_key": "mehltau", "plant_ids": [p["id"]]}).json()
        a = c.post(f"/api/plants/{p['id']}/abort", json={"reason": "zu tief gesetzt"}).json()
        assert a["status"] == "abgebrochen" and a["ended_on"] and a["end_reason"] == "zu tief gesetzt"
        assert c.get(f"/api/plants/{p['id']}").json()["phase"]["phase"] == "abgebrochen"
        assert c.get(f"/api/pests/cases/{case['id']}").json()["status"] == "erledigt"
        assert c.post(f"/api/plants/{p['id']}/abort", json={}).status_code == 400
        today_ids = [s["plant"]["id"] for s in c.get("/api/today").json()["runs"][0]["plants"]]
        assert p["id"] not in today_ids

        zelt = c.post("/api/pests/cases", json={"run_id": run["id"], "pest_key": "trauermuecken"}).json()
        r = c.post(f"/api/runs/{run['id']}/abort", json={"reason": "Neustart", "restart": {
            "name": "Run 2", "plants": 3, "germ_method": "h2o2", "soaked_at": "2026-10-31T20:00:00"}}).json()
        new = r["new_run"]
        assert new["status"] == "aktiv" and new["setup_id"] == run["setup_id"] and new["light_hours"] == run["light_hours"]
        assert len(r["plants"]) == 3 and r["plants"][0]["soaked_on"] == "2026-10-31"
        old = c.get(f"/api/runs/{run['id']}").json()
        assert old["run"]["status"] == "abgebrochen" and all(x["status"] != "aktiv" for x in old["plants"])
        assert c.get(f"/api/pests/cases/{zelt['id']}").json()["run_id"] == new["id"]
        t = c.get("/api/today").json()["runs"]
        assert [x["run"]["id"] for x in t] == [new["id"]] and len(t[0]["plants"]) == 3
        assert t[0]["tasks"] or c.get("/api/tasks").json()
        assert c.get("/api/household").json()["living_plants"] >= 0


def test_restart_then_seeds_auto_name():
    with TestClient(app) as c:
        run = c.get("/api/today").json()["runs"][0]["run"]
        r = c.post(f"/api/runs/{run['id']}/abort", json={"reason": "Keimt nicht", "restart": True}).json()
        new = r["new_run"]
        assert new["name_auto"] and any(x in new["name"] for x in ("Frühling", "Sommer", "Herbst", "Winter"))
        assert new["name"] != run["name"] and not r["plants"]
        strain = c.get("/api/strains").json()[0]
        out = c.post(f"/api/runs/{new['id']}/seeds", json={"rows": [{"strain_id": strain["id"], "count": 2}],
                                                           "germ_method": "h2o2", "soaked_at": "2026-10-31T18:30:00"}).json()
        assert len(out["plants"]) == 2 and out["run"]["name"].startswith(strain["name"])
        assert out["plants"][1]["name"] == "Pflanze 2" and out["plants"][0]["soaked_at"].startswith("2026-10-31T18:30")
        assert c.post(f"/api/runs/{new['id']}/seeds", json={"rows": []}).status_code == 400
        renamed = c.patch(f"/api/runs/{new['id']}", json={"name": "Mein Grow"}).json()
        assert renamed["name"] == "Mein Grow" and not renamed["name_auto"]
        c.post(f"/api/runs/{new['id']}/seeds", json={"rows": [{"strain_id": strain["id"], "count": 1}]})
        assert c.get(f"/api/runs/{new['id']}").json()["run"]["name"] == "Mein Grow"
        blank = c.post("/api/runs", json={"setup_id": run["setup_id"], "name": ""}).json()
        assert blank["name_auto"] and blank["name"].startswith("Grow – ")


def test_delete_run_moves_open_items():
    with TestClient(app) as c:
        keep = c.get("/api/today").json()["runs"][0]["run"]
        extra = c.post("/api/runs", json={"setup_id": keep["setup_id"], "name": "", "status": "abgebrochen"}).json()
        c.post(f"/api/runs/{extra['id']}/seeds", json={"rows": [{"strain_id": 1, "count": 2}]})
        t = c.post("/api/tasks", json={"title": "Test", "run_id": extra["id"], "interval_days": 7}).json()
        moved = c.delete(f"/api/runs/{extra['id']}").json()["moved_to"]
        assert moved and moved != extra["id"] and c.get(f"/api/runs/{moved}").json()["run"]["status"] == "aktiv"
        assert c.get(f"/api/runs/{extra['id']}").status_code == 404
        assert next(x for x in c.get("/api/tasks").json() if x["id"] == t["id"])["run_id"] == moved


def test_strain_info(monkeypatch):
    from app import strain_info
    raw = """Recherche …
```json
{"name": "White Truffle Auto", "breeder": "Zamnesia Seeds", "auto": true, "genetics": "GG x PBB x Ruderalis",
 "type": "60 % Indica", "thc": "23 %", "seed_to_harvest_days": "63", "max_height_cm": 100, "specials": ["kompakt"],
 "training": [{"key": "lst", "rating": "top", "reason": "buschig"}, {"key": "quatsch", "rating": "top"},
              {"key": "mainlining", "rating": "nein", "reason": "zu kurz"}]}
```"""
    parsed = strain_info.to_strain(strain_info._extract_json(raw), [{"url": "https://x", "title": "X"}], "internet")
    assert parsed["fields"]["seed_to_harvest_days"] == 63 and len(parsed["info"]["training"]) == 2

    async def fake(name, breeder="", auto=None):
        return parsed
    with TestClient(app) as c:
        assert c.post("/api/strains/lookup", json={"name": "White Truffle Auto"}).status_code == 502  # kein Schlüssel
        monkeypatch.setattr(strain_info, "lookup", fake)
        st = c.post("/api/strains", json={"name": "White Truffle Auto", "breeder": "Zamnesia Seeds"}).json()
        d = c.get(f"/api/strains/{st['id']}").json()
        assert d["training"] and d["info"] == {} and d["lookup_available"] is False
        r = c.post(f"/api/strains/{st['id']}/refresh").json()
        assert r["seed_to_harvest_days"] == 63 and r["info"]["thc"] == "23 %"
        assert r["training"][0]["key"] == "lst" and r["training"][-1]["rating"] == "nein"
        assert c.post("/api/strains/lookup", json={"name": "X"}).json()["fields"]["name"] == "White Truffle Auto"
