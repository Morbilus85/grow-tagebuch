import io
import os
import tempfile
import time

os.environ.setdefault("GROW_DATA_DIR", tempfile.mkdtemp())

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import ai_chat  # noqa: E402
from app.main import app  # noqa: E402


def _jpg():
    buf = io.BytesIO()
    Image.new("RGB", (2000, 1500), (40, 140, 40)).save(buf, "JPEG")
    return buf.getvalue()


def _wait(c, cid):
    for _ in range(100):
        d = c.get(f"/api/ai/chats/{cid}").json()
        if not d["chat"]["busy"]:
            return d
        time.sleep(0.05)
    raise AssertionError("keine Antwort")


def test_check_chat_flow(monkeypatch):
    sent = []

    async def fake_ask(messages):
        sent.append(messages)
        n = len(sent)
        return ({"reply": f"Antwort {n}", "ampel": "beobachten" if n == 1 else "unauffaellig",
                 "findings": [{"title": "Leicht hell", "confidence": "niedrig", "evidence": "Farbe", "against": "Sämling"}],
                 "next_steps": ["pH prüfen"], "comparison": "",
                 "photo_requests": [{"what": "Blattunterseite", "why": "Schädlinge ausschließen"}] if n == 1 else [],
                 "suggestions": [{"kind": "aufgabe", "title": "pH Runoff messen", "text": "beim nächsten Gießen",
                                  "due_in_days": 1, "interval_days": 0},
                                 {"kind": "notiz", "title": "Beobachtung", "text": "Blätter hell", "due_in_days": 0,
                                  "interval_days": 0}],
                 "summary": f"Fazit {n}"},
                {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 0})

    monkeypatch.setattr(ai_chat, "ask", fake_ask)
    monkeypatch.setattr(ai_chat, "api_key", lambda: "x")
    with TestClient(app) as c:
        run = c.get("/api/runs").json()[0]
        p = c.post("/api/plants", json={"run_id": run["id"], "name": "KI 1", "strain_id": 1,
                                         "planted_on": "2026-11-01", "sprouted_on": "2026-11-03"}).json()
        l = c.post("/api/logs", json={"plant_id": p["id"], "type": "watering", "volume_l": 0.2, "ph_in": 6.3}).json()
        ph = c.post(f"/api/logs/{l['id']}/photos", files={"file": ("a.jpg", _jpg(), "image/jpeg")}).json()

        # Check ohne explizite Fotos nimmt das neueste Foto der Pflanze
        chat = c.post("/api/ai/chats", json={"kind": "check", "plant_id": p["id"], "text": "Blätter hell?"}).json()
        d = _wait(c, chat["id"])
        assert d["chat"]["ampel"] == "beobachten" and d["chat"]["summary"] == "Fazit 1"
        assert d["messages"][0]["photo_ids"] == [ph["id"]]
        assert d["chat"]["cost_usd"] == round((1000 * 4 + 500 * 20) / 1e6, 4)
        first = sent[0][0]["content"]
        assert any(b["type"] == "image" for b in first)
        ctx = first[0]["text"]
        assert "KI 1" in ctx and "Inventar" in ctx and "pH 6,3" in ctx
        assert first[-1]["cache_control"]["type"] == "ephemeral"

        # Zeitstrahl-Eintrag
        logs = c.get(f"/api/logs?plant_id={p['id']}").json()
        entry = next(x for x in logs if x["type"] == "ai_check")
        assert "Beobachten" in entry["text"] and "Fazit 1" in entry["text"]

        # Angefordertes Foto hochladen und Rückfrage senden
        ph2 = c.post(f"/api/ai/chats/{chat['id']}/photos", files={"file": ("b.jpg", _jpg(), "image/jpeg")},
                     data={"what": "Blattunterseite"}).json()
        assert c.post(f"/api/ai/chats/{chat['id']}/messages", json={"text": "Hier", "photo_ids": [ph2["id"]]}).json()["ok"]
        d = _wait(c, chat["id"])
        assert len(d["messages"]) == 4 and d["chat"]["ampel"] == "unauffaellig"
        assert [m["role"] for m in sent[1]] == ["user", "assistant", "user"]
        assert sent[1][1]["content"][0]["text"].startswith("{")
        logs = c.get(f"/api/logs?plant_id={p['id']}").json()
        assert len([x for x in logs if x["type"] == "ai_check"]) == 1
        assert any(x["type"] == "observation" and "Blattunterseite" in x["text"] for x in logs)

        # Vorschläge übernehmen
        msg = d["messages"][1]
        t = c.post(f"/api/ai/chats/{chat['id']}/apply", json={"message_id": msg["id"], "index": 0}).json()
        assert t["applied"] and t["task_id"]
        assert any(x["title"] == "pH Runoff messen" for x in c.get("/api/tasks").json())
        n = c.post(f"/api/ai/chats/{chat['id']}/apply", json={"message_id": msg["id"], "index": 1}).json()
        assert n["log_id"]

        # Zweiter Check bekommt das Fazit und das Vergleichsfoto des ersten
        chat2 = c.post("/api/ai/chats", json={"kind": "check", "plant_id": p["id"], "photo_ids": [ph2["id"]]}).json()
        assert chat2["previous_photo_id"] == ph["id"]
        _wait(c, chat2["id"])
        txt = " ".join(b.get("text", "") for b in sent[2][0]["content"])
        assert "Fazit 2" in txt and "letzten Check" in txt

        # Frage am Zelt
        setup_id = run["setup_id"]
        q = c.post("/api/ai/chats", json={"kind": "frage", "setup_id": setup_id, "text": "Wann gießen?"}).json()
        _wait(c, q["id"])
        assert "Klima" in sent[3][0]["content"][0]["text"]
        assert len(c.get(f"/api/ai/chats?setup_id={setup_id}").json()) == 1
        assert len(c.get(f"/api/ai/chats?plant_id={p['id']}").json()) == 2

        # Fehler → retry
        async def broken(messages):
            raise RuntimeError("Kein Guthaben")
        monkeypatch.setattr(ai_chat, "ask", broken)
        c.post(f"/api/ai/chats/{q['id']}/messages", json={"text": "Und morgen?"})
        d = _wait(c, q["id"])
        assert d["chat"]["error"] == "Kein Guthaben"
        monkeypatch.setattr(ai_chat, "ask", fake_ask)
        c.post(f"/api/ai/chats/{q['id']}/retry")
        assert not _wait(c, q["id"])["chat"]["error"]

        # Löschen entfernt den Zeitstrahl-Eintrag, Fotos bleiben
        assert c.delete(f"/api/ai/chats/{chat['id']}").json()["ok"]
        logs = c.get(f"/api/logs?plant_id={p['id']}").json()
        assert len([x for x in logs if x["type"] == "ai_check"]) == 1
        assert c.get(f"/api/photos/{ph2['id']}").status_code == 200
        assert c.delete(f"/api/plants/{p['id']}").json()["ok"]
        assert c.get(f"/api/ai/chats?plant_id={p['id']}").json() == []


def test_check_requires_plant_and_frage_text(monkeypatch):
    monkeypatch.setattr(ai_chat, "api_key", lambda: "x")
    with TestClient(app) as c:
        assert c.post("/api/ai/chats", json={"kind": "check", "setup_id": 1}).status_code == 400
        assert c.post("/api/ai/chats", json={"kind": "frage", "setup_id": 1, "text": ""}).status_code == 400
