"""Living-Soil-Rechner."""
from __future__ import annotations

from typing import Optional

from ..living_soil_data import INGREDIENTS, RECIPES, ROLE_LABEL, TEAS

ING = {i["key"]: i for i in INGREDIENTS}
REC = {r["key"]: r for r in RECIPES}


def _round(v: float, unit: str) -> float:
    if unit == "l":
        return round(v, 1)
    return round(v) if v >= 20 else round(v, 1)


def calculate(recipe_key: str, volume_l: float, choices: Optional[dict] = None, owned: Optional[set] = None,
              include_optional: bool = True) -> dict:
    r = REC[recipe_key]
    choices = choices or {}
    owned = owned or set()
    bulk = []
    for b in r["bulk"]:
        if choices.get(b["role"]) in b["options"]:
            key = choices[b["role"]]
        elif b["role"] == "basis":
            key = b["options"][0]  # ungedüngte Basis bevorzugen, auch wenn Light-Mix im Haus ist
        else:
            key = next((o for o in b["options"] if o in owned), b["options"][0])
        ing = ING[key]
        bulk.append({"role": b["role"], "role_label": ROLE_LABEL[b["role"]], "key": key, "name": ing["name"],
                     "share": b["share"], "amount": _round(b["share"] * volume_l, "l"), "unit": "l",
                     "options": [{"key": o, "name": ING[o]["name"]} for o in b["options"]],
                     "owned": key in owned, "note": b.get("note", "")})
    base_key = next((b["key"] for b in bulk if b["role"] == "basis"), None)
    amendments = []
    for a in r["amendments"]:
        if a.get("only_base") and a["only_base"] != base_key:
            continue
        if a.get("optional") and not include_optional:
            continue
        ing = ING[a["key"]]
        amount = _round(a["per_l"] * volume_l, ing["unit"]) if a.get("per_l") else None
        amendments.append({"key": a["key"], "name": ing["name"], "role_label": ROLE_LABEL[ing["role"]],
                           "per_l": a.get("per_l"), "amount": amount, "unit": ing["unit"], "optional": bool(a.get("optional")),
                           "owned": a["key"] in owned, "note": a.get("note", "")})
    missing = [x for x in bulk + amendments if not x["owned"] and not x.get("optional")]
    return {"recipe": {k: r[k] for k in ("key", "name", "type", "vegan", "summary", "rest_days", "steps", "warnings")},
            "volume_l": volume_l, "bulk": bulk, "amendments": amendments,
            "shopping": [{"name": x["name"], "amount": x["amount"], "unit": x["unit"]} for x in missing],
            "volume_note": ("Mengen pro Liter gebrauchter Erde." if r["type"] == "reamend" else
                            "Plane ca. 10 % mehr ein, als die Töpfe fassen – die Mischung setzt sich.")}


def teas_for_phase(phase: Optional[str]) -> list[dict]:
    group = {"seedling": "seedling", "veg": "veg", "bloom": "bloom", "flush": None}.get(phase or "", None)
    return [t for t in TEAS if group and group in t["phases"]]
