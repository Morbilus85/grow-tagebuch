"""RDWC-Reservoir: CANNA-Aqua-Schema, Ansatzrechner und Zustand des Tanks.

Grundsatz wie beim Gieß-Assistenten: Das Herstellerschema liefert die Dosis (Mitte der Spanne),
die App rechnet nur auf die Tankmenge um und warnt – sie erhöht nie über das Schema hinaus.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

CANNA_AQUA_URL = "https://www.growmart.de/mediafiles/Sonstiges/Canna/duengeschema-canna-aqua-de-en.pdf"
CANNA_AQUA_RETRIEVED = "2026-11-25"

# CANNA Aqua (rezirkulierend), ml je Liter Wasser = Herstellerangabe ml/10 l geteilt durch 10.
# dose: (min, max); Vega/Flores sind Zweikomponenten – A und B jeweils diese Menge.
CANNA_AQUA = [
    {"key": "start", "label": "Start / Bewurzelung", "weeks": "< 1", "light": "18 h",
     "dose": {"canna_aqua_vega_a": (1.5, 2.5), "canna_aqua_vega_b": (1.5, 2.5), "canna_rhizotonic": (4, 4)},
     "ec_plus": (0.7, 1.1)},
    {"key": "veg1", "label": "Wachstum I", "weeks": "0–3", "light": "18 h",
     "dose": {"canna_aqua_vega_a": (2, 3), "canna_aqua_vega_b": (2, 3), "canna_rhizotonic": (2, 2), "cannazym": (2.5, 2.5)},
     "ec_plus": (0.9, 1.3)},
    {"key": "veg2", "label": "Wachstum II (Stretch nach Umstellung)", "weeks": "2–4", "light": "12 h",
     "dose": {"canna_aqua_vega_a": (2.5, 3.5), "canna_aqua_vega_b": (2.5, 3.5), "canna_rhizotonic": (2, 2),
              "cannazym": (2.5, 2.5), "canna_boost": (2, 2)},
     "ec_plus": (1.2, 1.6)},
    {"key": "bloom1", "label": "Blüte I", "weeks": "2–3", "light": "12 h",
     "dose": {"canna_aqua_flores_a": (3, 4), "canna_aqua_flores_b": (3, 4), "canna_rhizotonic": (0.5, 0.5),
              "cannazym": (2.5, 2.5), "canna_boost": (2, 4)},
     "ec_plus": (1.4, 1.8)},
    {"key": "bloom2", "label": "Blüte II (PK-Woche)", "weeks": "1", "light": "12 h",
     "dose": {"canna_aqua_flores_a": (3, 4), "canna_aqua_flores_b": (3, 4), "canna_rhizotonic": (0.5, 0.5),
              "cannazym": (2.5, 2.5), "canna_boost": (2, 4), "canna_pk_13_14": (1.5, 1.5)},
     "ec_plus": (1.6, 2.0)},
    {"key": "bloom3", "label": "Blüte III", "weeks": "2–3", "light": "12 h",
     "dose": {"canna_aqua_flores_a": (2, 3), "canna_aqua_flores_b": (2, 3), "canna_rhizotonic": (0.5, 0.5),
              "cannazym": (2.5, 2.5), "canna_boost": (2, 4)},
     "ec_plus": (1.0, 1.4)},
    {"key": "flush", "label": "Abreifen / Spülen", "weeks": "1–2", "light": "10–12 h",
     "dose": {"cannazym": (2.5, 5), "canna_boost": (2, 4)},
     "ec_plus": (0.0, 0.0)},
]
STAGES = {s["key"]: s for s in CANNA_AQUA}
ORDER = ["canna_aqua_vega_a", "canna_aqua_flores_a", "canna_aqua_vega_b", "canna_aqua_flores_b",
         "canna_rhizotonic", "cannazym", "canna_boost", "canna_pk_13_14"]

PH_TARGET = (5.8, 6.2)  # CANNA erlaubt 5,2–6,2; im RDWC hält man die Mitte
WATER_TEMP = (18.0, 21.0)
WATER_TEMP_ALARM = 22.0
CHANGE_DAYS = 7  # Richtwert Komplettwechsel (Praxis, keine CANNA-Angabe)

# key, name, kind, application, dose_min, dose_max (ml/l), group, in_stock, notes
PRODUCTS = [
    ("canna_aqua_vega_a", "Aqua Vega A", "base", 1.5, 3.5, "", True, "Mineralisch, RDWC/Hydro. Nur mit Vega B, getrennt ins Wasser."),
    ("canna_aqua_vega_b", "Aqua Vega B", "base", 1.5, 3.5, "", True, "Nach Vega A einrühren, nie mit A im Konzentrat mischen."),
    ("canna_aqua_flores_a", "Aqua Flores A", "base", 2, 4, "", True, "Mineralisch, Blüte. Nur mit Flores B."),
    ("canna_aqua_flores_b", "Aqua Flores B", "base", 2, 4, "", True, "Nach Flores A einrühren."),
    ("canna_rhizotonic", "Rhizotonic", "root", 0.5, 4, "wurzel", True, "Wurzelstimulator (Algenextrakt)."),
    ("cannazym", "Cannazym", "stimulant", 2.5, 5, "enzym", True, "Enzyme gegen abgestorbene Wurzelteile."),
    ("canna_boost", "Cannaboost Accelerator", "stimulant", 2, 4, "", True, "Blühstimulator, Standard 2 ml/l, bis 4 ml/l."),
    ("canna_pk_13_14", "PK 13/14", "stimulant", 1.5, 1.5, "", False, "Nur eine Woche (Blüte II). Nicht vorhanden."),
]


def ensure_products(session) -> int:
    """Fehlende CANNA-Produkte anlegen (bestehende Einträge und Inventarstatus bleiben unangetastet)."""
    from sqlmodel import select

    from ..models import Product
    have = {p.key for p in session.exec(select(Product)).all()}
    n = 0
    for key, name, kind, mn, mx, grp, stock, notes in PRODUCTS:
        if key in have:
            continue
        session.add(Product(key=key, name=name, brand="CANNA", kind=kind, form="fluessig", unit="ml",
                            application=["reservoir"], label_dose_min=mn, label_dose_max=mx, effect_group=grp,
                            in_stock=stock, notes=notes))
        n += 1
    if n:
        session.commit()
    return n


def suggest_stage(phases: list) -> str:
    """Schema-Phase aus den Pflanzenphasen (erste aktive Pflanze zählt). Nur Vorschlag."""
    for ph in phases:
        p = ph.get("phase")
        if p in ("keimung", "seedling"):
            return "start" if (ph.get("day") or 0) <= 7 else "veg1"
        if p == "veg":
            return "veg1"
        if p == "flush":
            return "flush"
        if p == "bloom":
            w = ph.get("bloom_week") or 1
            return "veg2" if w <= 2 else "bloom1" if w <= 5 else "bloom2" if w == 6 else "bloom3"
    return "start"


def _de(x) -> str:
    return f"{x:g}".replace(".", ",")


def _mid(r):
    return round((r[0] + r[1]) / 2, 2)


def recipe(stage_key: str, liters: float, water_ec: Optional[float], products: dict) -> dict:
    """products: {key: Product} – für Namen und Inventar. Liefert Mengen in Reihenfolge des Einrührens."""
    st = STAGES.get(stage_key)
    if not st:
        raise ValueError("Unbekannte Phase")
    items, missing = [], []
    for key in ORDER:
        if key not in st["dose"]:
            continue
        lo, hi = st["dose"][key]
        p = products.get(key)
        name = p.name if p else key
        if p is not None and not p.in_stock:
            missing.append(name)
            continue
        per_l = _mid((lo, hi))
        items.append({"key": key, "name": name, "per_l": per_l, "range": [lo, hi],
                      "total_ml": round(per_l * liters, 1), "unit": "ml"})
    wec = water_ec if water_ec is not None else 0.0
    lo, hi = st["ec_plus"]
    notes = ["Komponenten einzeln ins Wasser und jeweils gut umrühren: erst A, dann B, danach die Zusätze. "
             "Konzentrate nie direkt miteinander mischen.",
             f"pH erst ganz zum Schluss messen und auf {_de(PH_TARGET[0])}–{_de(PH_TARGET[1])} einstellen "
             "(CANNA erlaubt 5,2–6,2)."]
    if missing:
        notes.append(f"Nicht vorrätig, deshalb weggelassen: {', '.join(missing)}.")
    if stage_key == "flush":
        notes.append("Abreifen: nur Wasser plus Cannazym/Boost, kein Grunddünger.")
    return {
        "stage": stage_key, "label": st["label"], "liters": liters, "items": items,
        "ec_plus": [lo, hi], "water_ec": water_ec,
        "ec_target": [round(lo + wec, 2), round(hi + wec, 2)],
        "ph_target": list(PH_TARGET), "notes": notes,
        "source": {"name": "CANNA Aqua Düngeschema", "url": CANNA_AQUA_URL, "retrieved_on": CANNA_AQUA_RETRIEVED},
    }


def status(logs: list, today: Optional[date] = None, live_water_temp: Optional[float] = None) -> dict:
    """logs: LogEntry type=reservoir, neueste zuerst."""
    today = today or date.today()
    last_change = next((l for l in logs if l.reservoir_action == "wechsel"), None)
    last_meas = next((l for l in logs if l.ec_in is not None or l.ph_in is not None or l.water_temp is not None), None)
    msgs = []
    out = {"last_change": None, "days_since_change": None, "change_due_in": None, "last": None, "messages": msgs,
           "ph_target": list(PH_TARGET), "water_temp_target": list(WATER_TEMP), "change_days": CHANGE_DAYS,
           "live_water_temp": live_water_temp}
    if last_change:
        d = (today - last_change.ts.date()).days
        out.update(last_change=last_change.ts.isoformat(), days_since_change=d, change_due_in=CHANGE_DAYS - d,
                   volume_l=last_change.volume_l)
        if d >= CHANGE_DAYS:
            msgs.append(f"Letzter Komplettwechsel vor {d} Tagen – Wechsel fällig (Richtwert alle {CHANGE_DAYS} Tage).")
    else:
        msgs.append("Noch kein Reservoir-Ansatz eingetragen.")
    if last_meas:
        out["last"] = {"ts": last_meas.ts.isoformat(), "ec": last_meas.ec_in, "ph": last_meas.ph_in,
                       "water_temp": last_meas.water_temp}
        if last_meas.ph_in is not None and not (PH_TARGET[0] - 0.2 <= last_meas.ph_in <= PH_TARGET[1] + 0.2):
            msgs.append(f"pH {_de(last_meas.ph_in)} außerhalb {_de(PH_TARGET[0])}–{_de(PH_TARGET[1])}.")
    wt = live_water_temp if live_water_temp is not None else (last_meas.water_temp if last_meas else None)
    if wt is not None and wt > WATER_TEMP_ALARM:
        msgs.append(f"Wassertemperatur {_de(wt)} °C – über {_de(WATER_TEMP_ALARM)} °C steigt das Risiko für Wurzelfäule.")
    return out


def as_schema() -> list:
    return [{"key": s["key"], "label": s["label"], "weeks": s["weeks"], "light": s["light"], "ec_plus": list(s["ec_plus"]),
             "dose": {k: list(v) for k, v in s["dose"].items()}} for s in CANNA_AQUA]

