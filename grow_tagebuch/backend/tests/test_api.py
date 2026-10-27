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
