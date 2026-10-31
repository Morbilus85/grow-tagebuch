"""Sorten-Steckbrief: Abruf aus dem Internet über die Claude-API (Websuche) und Trainings-Empfehlung."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Optional

import httpx

from .db import DATA_DIR
from .training_data import TECHNIQUES

log = logging.getLogger("grow.strain")

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5-5"

# Bewertung je Trainingstechnik im Steckbrief
RATINGS = {"top": "besonders geeignet", "gut": "geeignet", "vorsicht": "mit Vorsicht", "nein": "ungeeignet"}


def api_key() -> str:
    p = DATA_DIR / "options.json"
    try:
        return (json.loads(p.read_text()).get("anthropic_api_key") or "").strip() if p.exists() else ""
    except (json.JSONDecodeError, OSError):
        return ""


def _prompt(name: str, breeder: str, auto: Optional[bool]) -> str:
    techniques = "\n".join(f"- {t['key']}: {t['name']}" for t in TECHNIQUES)
    typ = "Autoflower" if auto else ("photoperiodisch" if auto is False else "Typ unbekannt")
    return f"""Recherchiere die Cannabis-Sorte „{name}“ vom Breeder „{breeder or 'unbekannt'}“ ({typ}).
Nutze bevorzugt die Herstellerseite (Datenblatt) und ergänze Erfahrungswerte von Growern (z. B. Grow-Diaries, Seedfinder).
Es geht um einen Indoor-Grow in einem kleinen Zelt (ca. 80×80×180 cm, 20-l-Stofftöpfe, organisch mit BioBizz).

Antworte am Ende mit genau einem JSON-Block (```json … ```), alle Texte auf Deutsch, unbekannte Werte als null:
{{
  "name": "offizieller Sortenname",
  "breeder": "Breeder",
  "auto": true/false,
  "genetics": "Eltern/Kreuzung",
  "type": "z. B. 60 % Indica / 40 % Sativa",
  "thc": "z. B. 23 %",
  "cbd": "z. B. < 1 %",
  "seed_to_harvest_days": Zahl (Autos: Samen bis Ernte laut Breeder, Obergrenze) oder null,
  "flowering_days": Zahl (Photos: Blütedauer, Obergrenze) oder null,
  "seed_to_harvest_text": "Breeder-Angabe im Wortlaut, z. B. 8–9 Wochen",
  "grower_days": "typische tatsächliche Dauer laut Growern, z. B. 70–80 Tage",
  "max_height_cm": Zahl (Indoor, Breeder) oder null,
  "height_text": "z. B. Indoor 100 cm, Outdoor 130 cm",
  "yield_indoor": "z. B. bis 500 g/m²",
  "yield_outdoor": "z. B. bis 300 g/Pflanze",
  "difficulty": "leicht | mittel | schwer",
  "aroma": "Geschmack/Aroma",
  "terpenes": "Haupt-Terpene",
  "effect": "Wirkung",
  "structure": "Wuchsform, Stretch, Blattbild",
  "specials": ["Besonderheiten, z. B. schimmelanfällig, nährstoffhungrig, stark duftend"],
  "grow_tips": ["konkrete Anbautipps für diese Sorte"],
  "training": [{{"key": "Schlüssel aus der Liste", "rating": "top | gut | vorsicht | nein", "reason": "kurze Begründung für diese Sorte"}}]
}}

Bewerte unter "training" jede dieser Techniken (Schlüssel exakt übernehmen):
{techniques}
"""


def _extract_json(text: str) -> dict:
    m = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    raw = m[-1] if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


async def lookup(name: str, breeder: str = "", auto: Optional[bool] = None) -> dict:
    """Fragt Claude mit Websuche nach dem Steckbrief. Liefert {fields, info}."""
    key = api_key()
    if not key:
        raise RuntimeError("Kein Claude-API-Schlüssel hinterlegt (Add-on → Konfiguration → anthropic_api_key).")
    messages = [{"role": "user", "content": _prompt(name, breeder, auto)}]
    body = {"model": MODEL, "max_tokens": 4000, "messages": messages,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    texts: list[str] = []
    sources: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=180) as client:
        for _ in range(4):  # pause_turn: Antwort fortsetzen lassen
            r = await client.post(API_URL, headers=headers, json=body)
            if r.status_code != 200:
                raise RuntimeError(f"Claude-API: {r.status_code} {r.text[:300]}")
            data = r.json()
            for block in data.get("content", []):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                    for c in block.get("citations") or []:
                        if c.get("url"):
                            sources.setdefault(c["url"], c.get("title") or c["url"])
            if data.get("stop_reason") != "pause_turn":
                break
            messages.append({"role": "assistant", "content": data["content"]})
    try:
        d = _extract_json("\n".join(texts))
    except (ValueError, json.JSONDecodeError) as e:
        log.warning("Steckbrief nicht lesbar: %s", e)
        raise RuntimeError("Die Antwort enthielt keinen lesbaren Steckbrief – bitte noch einmal versuchen.")
    return to_strain(d, list({"url": u, "title": t} for u, t in sources.items())[:8], source="internet")


def _int(v) -> Optional[int]:
    try:
        return int(round(float(v))) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def to_strain(d: dict, sources: list, source: str) -> dict:
    """Steckbrief-Dict → Felder für das Strain-Modell + info-JSON."""
    valid = {t["key"] for t in TECHNIQUES}
    training = [t for t in (d.get("training") or []) if isinstance(t, dict) and t.get("key") in valid
                and t.get("rating") in RATINGS]
    fields = {k: v for k, v in {
        "name": d.get("name"), "breeder": d.get("breeder"),
        "auto": d.get("auto") if isinstance(d.get("auto"), bool) else None,
        "genetics": d.get("genetics"),
        "seed_to_harvest_days": _int(d.get("seed_to_harvest_days")),
        "flowering_days": _int(d.get("flowering_days")),
        "max_height_cm": _int(d.get("max_height_cm")),
    }.items() if v not in (None, "")}
    info = {k: d.get(k) for k in ("type", "thc", "cbd", "seed_to_harvest_text", "grower_days", "height_text",
                                  "yield_indoor", "yield_outdoor", "difficulty", "aroma", "terpenes", "effect",
                                  "structure") if d.get(k)}
    info["specials"] = [s for s in (d.get("specials") or []) if s]
    info["grow_tips"] = [s for s in (d.get("grow_tips") or []) if s]
    info["training"] = training
    info["sources"] = sources
    info["source"] = source
    info["updated_at"] = datetime.now().isoformat(timespec="minutes")
    return {"fields": fields, "info": info}


def training_for(strain, tent_room_cm: Optional[float] = None) -> list[dict]:
    """Trainings-Empfehlung für eine Sorte: Steckbrief, sonst Katalog-Eignung für Auto/Photo."""
    info = (strain.info or {}) if strain else {}
    names = {t["key"]: t["name"] for t in TECHNIQUES}
    if info.get("training"):
        out = [{**t, "name": names[t["key"]], "label": RATINGS[t["rating"]]} for t in info["training"]]
    else:
        auto = strain.auto if strain else True
        conv = {"empfohlen": "gut", "bedingt": "vorsicht", "abraten": "nein"}
        out = []
        for t in TECHNIQUES:
            rating = conv.get(t["auto"] if auto else t.get("photo", "empfohlen"), "gut")
            out.append({"key": t["key"], "name": t["name"], "rating": rating, "label": RATINGS[rating],
                        "reason": "Allgemeine Eignung für " + ("Autoflower" if auto else "photoperiodische Sorten")})
    if strain and strain.max_height_cm and tent_room_cm and strain.max_height_cm > tent_room_cm:
        for t in out:
            if t["key"] in ("lst", "leaf_tucking") and t["rating"] != "nein":
                t["rating"], t["label"] = "top", RATINGS["top"]
                t["reason"] = (t.get("reason") or "") + f" Sorte wird bis {strain.max_height_cm} cm hoch, im Zelt ist Platz " \
                              f"für ca. {tent_room_cm:.0f} cm – flach halten."
    order = {"top": 0, "gut": 1, "vorsicht": 2, "nein": 3}
    return sorted(out, key=lambda t: order[t["rating"]])
