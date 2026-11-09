"""Steckbriefe für Wasser (Trinkwasseranalyse des Versorgers) und Erde (Herstellerangaben) über die Claude-API."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from .strain_info import _extract, _headers, _research, api_key

log = logging.getLogger("grow.material")

_S = {"type": "string"}
_N = {"type": "number"}
_LIST = {"type": "array", "items": _S}


def _schema(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


# ---------------------------------------------------------------- Wasser

WATER_NUM = {  # Schema-Feld → Feld im WaterProfile
    "ph": "ph", "calcium_mg_l": "ca_mg_l", "magnesium_mg_l": "mg_mg_l", "sodium_mg_l": "na_mg_l",
    "potassium_mg_l": "k_mg_l", "chloride_mg_l": "cl_mg_l", "sulfate_mg_l": "so4_mg_l", "nitrate_mg_l": "no3_mg_l",
    "acid_capacity_mmol_l": "acid_capacity_mmol", "total_hardness_dh": "hardness_dh",
    "carbonate_hardness_dh": "carbonate_hardness_dh",
}
WATER_SCHEMA = _schema({
    "supplier": {**_S, "description": "Wasserversorger, z. B. Stadtwerke Essen"},
    "supply_area": {**_S, "description": "Wasserwerk bzw. Versorgungsgebiet, zu dem die Werte gehören"},
    "analysis_date": {**_S, "description": "Stand der Analyse, z. B. Jahresmittel 2025"},
    "conductivity_us_cm": {**_N, "description": "elektrische Leitfähigkeit bei 25 °C in µS/cm, unbekannt 0"},
    **{k: {**_N, "description": "unbekannt 0"} for k in WATER_NUM},
    "hardness_range": {"type": "string", "enum": ["weich", "mittel", "hart", "unbekannt"]},
    "notes": {**_LIST, "description": "Hinweise: mehrere Versorgungsgebiete, Mischwasser, Besonderheiten fürs Gießen"},
})


def _water_prompt(city: str) -> str:
    return f"""Suche die aktuelle Trinkwasseranalyse für „{city}“ (Deutschland).
Verwende ausschließlich die offiziellen Angaben des örtlichen Wasserversorgers (Trinkwasseranalyse, Wasserqualitäts-PDF,
Härtebereich-Seite). Keine Vergleichsportale. Wenn der Ort mehrere Versorgungsgebiete oder Wasserwerke hat, nimm das
Gebiet, das zum angegebenen Stadtteil passt; ohne Stadtteil das größte bzw. typische und nenne die anderen kurz.
Fasse auf Deutsch zusammen: Versorger, Versorgungsgebiet/Wasserwerk, Stand der Analyse, Leitfähigkeit (µS/cm bei 25 °C), pH,
Calcium, Magnesium, Natrium, Kalium, Chlorid, Sulfat, Nitrat (mg/l), Säurekapazität bis pH 4,3 (mmol/l), Gesamthärte und
Karbonathärte (°dH), Härtebereich. Ergänze kurze Hinweise, was das für organisches Gießen mit BioBizz bedeutet
(pH-Korrektur, Calcium/Magnesium-Bedarf)."""


async def water_lookup(city: str) -> dict:
    key = _key()
    sources: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=180) as client:
        headers = _headers(key)
        research = await _research(client, headers, city, _water_prompt(city), sources, max_uses=5)
        if not research:
            raise RuntimeError("Die Recherche hat nichts geliefert – bitte noch einmal versuchen.")
        d = await _extract(client, headers, city, research, WATER_SCHEMA,
                           f"Übertrage diese Recherche zur Trinkwasseranalyse für „{city}“ in das Schema. Texte auf "
                           "Deutsch, unbekannte Texte leer, unbekannte Zahlen 0. Keine Werte erfinden.")
    if d is None:
        raise RuntimeError("Die Antwort enthielt keine lesbaren Wasserwerte – bitte noch einmal versuchen.")
    return to_water(d, _src(sources))


def to_water(d: dict, sources: list) -> dict:
    fields = {dst: _num(d.get(src)) for src, dst in WATER_NUM.items()}
    us = _num(d.get("conductivity_us_cm"))
    fields["ec"] = round(us / 1000, 3) if us else None  # App rechnet in mS/cm
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        raise RuntimeError("Keine Wasserwerte gefunden – Ort genauer angeben (z. B. mit Stadtteil).")
    info = {k: d.get(k) for k in ("supplier", "supply_area", "analysis_date", "hardness_range") if d.get(k)
            and d.get(k) != "unbekannt"}
    info.update(notes=[n for n in (d.get("notes") or []) if n], sources=sources, source="internet",
                updated_at=datetime.now().isoformat(timespec="minutes"))
    return {"fields": fields, "info": info}


# ---------------------------------------------------------------- Erde

SOIL_SCHEMA = _schema({
    "product": {**_S, "description": "offizieller Produktname"},
    "manufacturer": _S,
    "fertilization": {"type": "string", "enum": ["stark vorgedüngt", "vorgedüngt", "leicht vorgedüngt", "ungedüngt", "unbekannt"]},
    "organic": {**_S, "description": "z. B. bio-zertifiziert (FiBL-Liste), organisch, mineralisch gedüngt"},
    "components": {"type": "array", "items": _schema({
        "name": _S, "share": {**_S, "description": "Anteil laut Hersteller, z. B. 30 % oder leer"}})},
    "fertilizers": {**_LIST, "description": "enthaltene Dünger, z. B. Guano, Horn-, Knochen-, Blutmehl, Kompost"},
    "n_mg_l": {**_N, "description": "Stickstoff N in mg/l, unbekannt 0"},
    "p2o5_mg_l": {**_N, "description": "Phosphat P2O5 in mg/l, unbekannt 0"},
    "k2o_mg_l": {**_N, "description": "Kaliumoxid K2O in mg/l, unbekannt 0"},
    "mg_mg_l": {**_N, "description": "Magnesium in mg/l, unbekannt 0"},
    "salt_g_l": {**_N, "description": "Salzgehalt in g/l, unbekannt 0"},
    "ph": {**_S, "description": "pH-Wert laut Hersteller, z. B. 5,5–6,5"},
    "structure": {**_S, "description": "Struktur, Perlit, Belüftung, Wasserhaltevermögen"},
    "nutrient_weeks": {"type": "integer", "description": "Herstellerangabe: Wochen, die die Vorratsdüngung reicht, unbekannt 0"},
    "schedule_type": {"type": "string", "enum": ["all_mix", "light_mix", "living_soil"],
                      "description": "all_mix = vorgedüngt, light_mix = schwach/ungedüngt, living_soil = nur Wasser/Tees"},
    "feeding_notes": {**_LIST, "description": "konkrete Hinweise zur Abstimmung mit BioBizz und eigenen Zusätzen"},
    "specials": _LIST,
})


def _soil_prompt(product: str, mix: str) -> str:
    return f"""Erstelle einen Steckbrief für die Pflanzerde „{product}“.
Verwende vorrangig die Angaben des Herstellers (Produktseite, Datenblatt, Verpackungsaufdruck). Händlerseiten nur, wenn
sie die Herstellerangaben wiedergeben; Foren nicht.
Fasse auf Deutsch zusammen: offizieller Name, Hersteller, Bio/organisch, Zusammensetzung mit Anteilen, enthaltene Dünger,
Nährstoffgehalte (N, P2O5, K2O, Mg in mg/l), Salzgehalt (g/l), pH, Struktur/Perlit, wie lange die Vorratsdüngung laut
Hersteller reicht, Besonderheiten.
Anwendung: Cannabis-Autoflower indoor, 20-l-Stofftöpfe, organisch mit BioBizz (Bio-Grow, Bio-Bloom, Top-Max, Alg-A-Mic,
CalMag). Eigene Mischung: {mix or 'Erde pur'}. Gib konkrete Hinweise, ab wann und wie stark mit BioBizz gedüngt werden sollte
und ob das All-Mix- oder Light-Mix-Schema passt."""


async def soil_lookup(product: str, mix: str = "") -> dict:
    key = _key()
    sources: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=180) as client:
        headers = _headers(key)
        research = await _research(client, headers, product, _soil_prompt(product, mix), sources, max_uses=4)
        if not research:
            raise RuntimeError("Die Recherche hat nichts geliefert – bitte noch einmal versuchen.")
        d = await _extract(client, headers, product, research, SOIL_SCHEMA,
                           f"Übertrage diese Recherche zur Erde „{product}“ vollständig in den Steckbrief. Texte auf "
                           "Deutsch, unbekannte Texte leer, unbekannte Zahlen 0. Keine Werte erfinden.")
    if d is None:
        raise RuntimeError("Die Antwort enthielt keinen lesbaren Steckbrief – bitte noch einmal versuchen.")
    return to_soil(d, _src(sources))


def to_soil(d: dict, sources: list) -> dict:
    info = {k: d.get(k) for k in ("product", "manufacturer", "fertilization", "organic", "ph", "structure", "schedule_type")
            if d.get(k) and d.get(k) != "unbekannt"}
    for k in ("n_mg_l", "p2o5_mg_l", "k2o_mg_l", "mg_mg_l", "salt_g_l"):
        if _num(d.get(k)) is not None:
            info[k] = _num(d.get(k))
    weeks = _num(d.get("nutrient_weeks"))
    if weeks:
        info["nutrient_weeks"] = int(weeks)
    info["components"] = [c for c in (d.get("components") or []) if isinstance(c, dict) and c.get("name")]
    for k in ("fertilizers", "feeding_notes", "specials"):
        info[k] = [x for x in (d.get(k) or []) if x]
    info.update(sources=sources, source="internet", updated_at=datetime.now().isoformat(timespec="minutes"))
    return {"info": info}


# ---------------------------------------------------------------- Hilfen

def _key() -> str:
    key = api_key()
    if not key:
        raise RuntimeError("Kein Claude-API-Schlüssel hinterlegt (Add-on → Konfiguration → anthropic_api_key).")
    return key


def _src(sources: dict) -> list:
    return [{"url": u, "title": t} for u, t in sources.items()][:6]


def _num(v) -> Optional[float]:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None
