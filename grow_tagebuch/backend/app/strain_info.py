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


def _headers(key: str) -> dict:
    return {"authorization": f"Bearer {key}", "anthropic-version": "2023-06-01", "content-type": "application/json"}


def _error(r: httpx.Response) -> str:
    try:
        msg = r.json().get("error", {}).get("message", "")
    except ValueError:
        msg = r.text[:200]
    hints = {401: "Schlüssel ungültig oder abgelaufen.", 403: "Schlüssel hat keine Berechtigung.",
             400: "Anfrage abgelehnt – ist der Schlüssel auf einen Workspace beschränkt?",
             402: "Kein Guthaben – in der Console unter Billing aufladen.", 429: "Zu viele Anfragen – kurz warten."}
    if "credit" in msg.lower() or "balance" in msg.lower():
        return "Kein Guthaben – in der Claude Console unter Billing aufladen."
    return f"{hints.get(r.status_code, 'Claude-API-Fehler')} ({r.status_code}: {msg})"


async def test_key() -> dict:
    """Mini-Anfrage, um Schlüssel, Workspace und Guthaben zu prüfen."""
    key = api_key()
    if not key:
        return {"ok": False, "message": "Kein Schlüssel eingetragen."}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(API_URL, headers=_headers(key),
                              json={"model": MODEL, "max_tokens": 5, "messages": [{"role": "user", "content": "Antworte nur mit OK."}]})
    if r.status_code == 200:
        return {"ok": True, "message": "Schlüssel funktioniert."}
    return {"ok": False, "message": _error(r)}


def _prompt(name: str, breeder: str, auto: Optional[bool]) -> str:
    techniques = "\n".join(f"- {t['key']}: {t['name']}" for t in TECHNIQUES)
    typ = "Autoflower" if auto else ("photoperiodisch" if auto is False else "Typ unbekannt")
    return f"""Recherchiere die Cannabis-Sorte „{name}“ vom Breeder „{breeder or 'unbekannt'}“ ({typ}).
Nutze bevorzugt die Herstellerseite (Datenblatt) und ergänze Erfahrungswerte von Growern (z. B. Grow-Diaries, Seedfinder).
Es geht um einen Indoor-Grow in einem kleinen Zelt (ca. 80×80×180 cm, 20-l-Stofftöpfe, organisch mit BioBizz).

Fasse auf Deutsch zusammen: offizieller Name, Breeder, Auto oder Photo, Genetik, Indica/Sativa-Anteil, THC, CBD,
Samen bis Ernte bzw. Blütedauer und Indoor-Höhe: Halte für BEIDE Werte jede Quelle einzeln fest – Breeder, Seedbanks/Shops,
Datenbanken (Seedfinder, Leafly), einzelne Grow-Diaries und Forenberichte – jeweils mit Quelle und konkreter Zahl bzw. Spanne
(Tage bzw. cm) und kurzem Kontext (z. B. „Gießfehler“, „Licht 18/6“). Möglichst 4–8 Angaben je Wert, bei der Höhe
gezielt nach Endhöhen in Grow-Diaries suchen (z. B. „85 days – 97 cm“). Ertrag indoor/outdoor,
Schwierigkeit, Aroma, Terpene, Wirkung, Wuchsform/Stretch, Besonderheiten, konkrete Anbautipps.
Bewerte außerdem jede dieser Trainingstechniken für genau diese Sorte (besonders geeignet / geeignet / mit Vorsicht / ungeeignet, je kurze Begründung):
{techniques}
"""


_S = {"type": "string"}
_I = {"type": "integer"}
KINDS = {"breeder": "Breeder", "shop": "Shop", "datenbank": "Datenbank", "grower": "Grower/Forum"}
# Eine Angabe je Quelle; min = max bei Einzelwert
_CLAIMS = {"type": "array", "items": {"type": "object", "properties": {
    "source": {**_S, "description": "z. B. Zamnesia, Seedfinder, GrowDiaries (Nutzer xy)"},
    "kind": {"type": "string", "enum": list(KINDS)},
    "min": _I, "max": _I,
    "note": {**_S, "description": "kurzer Kontext, leer wenn keiner"}},
    "required": ["source", "kind", "min", "max", "note"], "additionalProperties": False}}
# Structured Outputs: alle Felder Pflicht, unbekannt = "" bzw. 0 (kaum Union-Typen, additionalProperties false)
SCHEMA = {
    "type": "object",
    "properties": {
        "name": _S, "breeder": _S, "auto": {"type": "boolean"}, "genetics": _S,
        "type": {**_S, "description": "z. B. 60 % Indica / 40 % Sativa"},
        "thc": {**_S, "description": "z. B. 23 %"}, "cbd": _S,
        "seed_to_harvest_days": {**_I, "description": "Autos: Samen bis Ernte laut Breeder in Tagen (Obergrenze), sonst 0"},
        "flowering_days": {**_I, "description": "Photos: Blütedauer laut Breeder in Tagen (Obergrenze), sonst 0"},
        "duration_claims": {**_CLAIMS, "description": "Jede Quelle einzeln: Autos Samen bis Ernte, Photos Blütedauer, in Tagen"},
        "seed_to_harvest_text": {**_S, "description": "Breeder-Angabe im Wortlaut, z. B. 8–9 Wochen (Breeder)"},
        "grower_days": {**_S, "description": "typische tatsächliche Dauer laut Growern"},
        "max_height_cm": {**_I, "description": "Indoor-Höhe laut Breeder in cm, unbekannt 0"},
        "height_claims": {**_CLAIMS, "description": "Jede Quelle einzeln: Indoor-Endhöhe in cm"},
        "height_text": _S, "yield_indoor": _S, "yield_outdoor": _S,
        "difficulty": {"type": "string", "enum": ["leicht", "mittel", "schwer", "unbekannt"]},
        "aroma": _S, "terpenes": _S, "effect": _S,
        "structure": {**_S, "description": "Wuchsform, Stretch, Blattbild"},
        "specials": {"type": "array", "items": _S},
        "grow_tips": {"type": "array", "items": _S},
        "training": {"type": "array", "items": {"type": "object", "properties": {
            "key": {"type": "string", "enum": [t["key"] for t in TECHNIQUES]},
            "rating": {"type": "string", "enum": list(RATINGS)},
            "reason": _S}, "required": ["key", "rating", "reason"], "additionalProperties": False}},
    },
    "additionalProperties": False,
}
SCHEMA["required"] = list(SCHEMA["properties"])


def _extract_json(text: str) -> dict:
    m = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    raw = m[-1] if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


async def lookup(name: str, breeder: str = "", auto: Optional[bool] = None) -> dict:
    """Schritt 1: Recherche mit Websuche (Freitext + Quellen). Schritt 2: Auslesen über festes Schema
    (Tool-Aufruf erzwingt gültiges JSON). Liefert {fields, info}."""
    key = api_key()
    if not key:
        raise RuntimeError("Kein Claude-API-Schlüssel hinterlegt (Add-on → Konfiguration → anthropic_api_key).")
    headers = _headers(key)
    texts: list[str] = []
    sources: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=180) as client:
        for attempt in range(2):  # leere Websuche kommt sporadisch vor → einmal wiederholen
            messages = [{"role": "user", "content": _prompt(name, breeder, auto)}]
            body = {"model": MODEL, "max_tokens": 6000, "messages": messages,
                    "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]}
            texts.clear()
            for _ in range(4):  # pause_turn: Antwort fortsetzen lassen
                r = await client.post(API_URL, headers=headers, json=body)
                if r.status_code != 200:
                    raise RuntimeError(_error(r))
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
            research = "".join(texts).strip()
            if research:
                break
            log.warning("Recherche zu %s leer (Versuch %d, stop_reason %s)", name, attempt + 1, data.get("stop_reason"))
        if not research:
            raise RuntimeError("Die Recherche hat nichts geliefert – bitte noch einmal versuchen.")
        extract = {
            "model": MODEL, "max_tokens": 8000,
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content":
                          f"Übertrage diese Recherche zur Sorte „{name}“ vollständig in den Steckbrief. Alle Texte auf Deutsch, "
                          f"unbekannte Texte leer, unbekannte Zahlen 0, jede Trainingstechnik genau einmal bewerten. "
                          f"duration_claims und height_claims mit jeder Einzelangabe aus der Recherche füllen "
                          f"(auch Höhen, die nebenbei in Diaries genannt werden).\n\n{research}"}],
        }
        r = await client.post(API_URL, headers=headers, json=extract)
        if r.status_code != 200:
            raise RuntimeError(_error(r))
        out = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        try:
            d = json.loads(out)
        except json.JSONDecodeError:
            d = None
    if not isinstance(d, dict):
        log.warning("Steckbrief nicht lesbar")
        raise RuntimeError("Die Antwort enthielt keinen lesbaren Steckbrief – bitte noch einmal versuchen.")
    return to_strain(d, [{"url": u, "title": t} for u, t in sources.items()][:8], source="internet")


def _int(v) -> Optional[int]:
    try:
        n = int(round(float(v))) if v not in (None, "") else None
        return n if n else None
    except (TypeError, ValueError):
        return None


def _claims(raw) -> tuple[list, Optional[int]]:
    """Quellenangaben bereinigen und mitteln: je Quelle die Mitte ihrer Spanne; Hersteller-Seite (Breeder, Shops,
    Datenbanken – oft abgeschriebenes Datenblatt) und Grower-Seite getrennt mitteln, dann beide Seiten 50/50."""
    out = []
    for c in raw or []:
        if not isinstance(c, dict):
            continue
        lo, hi = _int(c.get("min")), _int(c.get("max"))
        lo, hi = lo or hi, hi or lo
        if not lo:
            continue
        lo, hi = min(lo, hi), max(lo, hi)
        out.append({"source": (c.get("source") or "?").strip(), "kind": c.get("kind") if c.get("kind") in KINDS else "grower",
                    "min": lo, "max": hi, "note": (c.get("note") or "").strip()})
    sides = [[(c["min"] + c["max"]) / 2 for c in out if (c["kind"] == "grower") == g] for g in (False, True)]
    means = [sum(v) / len(v) for v in sides if v]
    return out, (round(sum(means) / len(means)) if means else None)


def to_strain(d: dict, sources: list, source: str) -> dict:
    """Steckbrief-Dict → Felder für das Strain-Modell + info-JSON.
    Gerechnet wird mit den realistischen Werten (Grower), die Breeder-Angaben landen nur im Steckbrief."""
    breeder = {"days": _int(d.get("seed_to_harvest_days")), "flowering_days": _int(d.get("flowering_days")),
               "height_cm": _int(d.get("max_height_cm"))}
    dur, dur_mean = _claims(d.get("duration_claims"))
    hgt, hgt_mean = _claims(d.get("height_claims"))
    auto = d.get("auto") if isinstance(d.get("auto"), bool) else None
    valid = {t["key"] for t in TECHNIQUES}
    training = [t for t in (d.get("training") or []) if isinstance(t, dict) and t.get("key") in valid
                and t.get("rating") in RATINGS]
    fields = {k: v for k, v in {
        "name": d.get("name"), "breeder": d.get("breeder"),
        "auto": d.get("auto") if isinstance(d.get("auto"), bool) else None,
        "genetics": d.get("genetics"),
        "seed_to_harvest_days": (dur_mean if auto is not False else None) or breeder["days"],
        "flowering_days": (dur_mean if auto is False else None) or breeder["flowering_days"],
        "max_height_cm": hgt_mean or breeder["height_cm"],
    }.items() if v not in (None, "")}
    info = {k: d.get(k) for k in ("type", "thc", "cbd", "seed_to_harvest_text", "grower_days", "height_text",
                                  "yield_indoor", "yield_outdoor", "difficulty", "aroma", "terpenes", "effect",
                                  "structure") if d.get(k) and d.get(k) != "unbekannt"}
    info["breeder_values"] = {k: v for k, v in breeder.items() if v}
    info["duration_claims"], info["height_claims"] = dur, hgt
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
