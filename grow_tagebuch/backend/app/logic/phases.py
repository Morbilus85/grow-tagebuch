"""Phasenmodell für Autos und Photos."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Optional

SEEDLING_DAYS = 14
FLUSH_DAYS = 7
AUTO_DEFAULT_TOTAL = 77
AUTO_PREFLOWER_SHARE = 0.35  # Vorblüte bei Autos grob nach gut einem Drittel der Laufzeit
PHOTO_DEFAULT_FLOWERING = 63

LABELS = {
    "geplant": "Geplant",
    "einweichen": "Einweichen",
    "keimung": "Keimung",
    "seedling": "Sämling",
    "veg": "Wachstum",
    "bloom": "Blüte",
    "flush": "Reife / nur Wasser",
    "harvest": "Erntereif",
    "geerntet": "Geerntet",
}


@dataclass
class PhaseInfo:
    phase: str
    label: str
    day: Optional[int] = None  # Tag seit Auflaufen (1 = Auflauftag)
    week: Optional[int] = None
    bloom_week: Optional[int] = None
    schedule_stage: Optional[str] = None  # seedling | veg | bloom_1..bloom_8 | flush | None
    preflower_date: Optional[date] = None
    preflower_estimated: bool = True
    harvest_date: Optional[date] = None
    days_to_harvest: Optional[int] = None
    auto_mapping_note: Optional[str] = None

    def dict(self):
        d = asdict(self)
        for k in ("preflower_date", "harvest_date"):
            if d[k]:
                d[k] = d[k].isoformat()
        return d


def _bloom_column(bloom_week: int, bloom_feed_weeks: float) -> int:
    """Streckt/staucht die 8 Blüte-Spalten des Herstellerschemas auf die echte Blütedauer."""
    n = max(round(bloom_feed_weeks), 1)
    if n == 1:
        return 1
    col = 1 + round((bloom_week - 1) * 7 / (n - 1))
    return max(1, min(8, col))


def compute(plant, strain, today: Optional[date] = None) -> PhaseInfo:
    today = today or date.today()
    if plant.harvested_on or plant.status == "geerntet":
        return PhaseInfo("geerntet", LABELS["geerntet"])
    if not plant.sprouted_on:
        if plant.planted_on:
            return PhaseInfo("keimung", LABELS["keimung"])
        if plant.soaked_on:
            return PhaseInfo("einweichen", LABELS["einweichen"])
        return PhaseInfo("geplant", LABELS["geplant"])

    day = (today - plant.sprouted_on).days + 1
    week = (day - 1) // 7 + 1
    auto = strain.auto if strain else True

    if auto:
        total = (strain.seed_to_harvest_days if strain and strain.seed_to_harvest_days else AUTO_DEFAULT_TOTAL)
        if plant.preflower_on:
            pf_day = (plant.preflower_on - plant.sprouted_on).days + 1
            estimated = False
        else:
            pf_day = round(total * AUTO_PREFLOWER_SHARE)
            estimated = True
        note = ("BioBizz veröffentlicht kein Auto-Schema – die Zuordnung der Blüte-Spalten auf die Sortendauer "
                "ist eine eigene Annahme.")
    else:
        flowering = (strain.flowering_days if strain and strain.flowering_days else PHOTO_DEFAULT_FLOWERING)
        if not plant.flip_on:
            ph = "seedling" if day <= SEEDLING_DAYS else "veg"
            return PhaseInfo(ph, LABELS[ph], day, week, schedule_stage=ph, preflower_date=None)
        pf_day = (plant.flip_on - plant.sprouted_on).days + 1
        total = pf_day - 1 + flowering
        estimated = False
        note = None

    preflower_date = plant.sprouted_on + timedelta(days=pf_day - 1)
    harvest_date = plant.sprouted_on + timedelta(days=total - 1)
    bloom_len = total - pf_day + 1
    bloom_feed_weeks = max((bloom_len - FLUSH_DAYS) / 7, 1)
    base = dict(day=day, week=week, preflower_date=preflower_date, preflower_estimated=estimated,
                harvest_date=harvest_date, days_to_harvest=(harvest_date - today).days, auto_mapping_note=note)

    if day <= SEEDLING_DAYS and day < pf_day:
        return PhaseInfo("seedling", LABELS["seedling"], schedule_stage="seedling", **base)
    if day < pf_day:
        return PhaseInfo("veg", LABELS["veg"], schedule_stage="veg", **base)
    if day > total:
        return PhaseInfo("harvest", LABELS["harvest"], schedule_stage=None, **base)
    if day > total - FLUSH_DAYS:
        return PhaseInfo("flush", LABELS["flush"], schedule_stage="flush", **base)
    bloom_week = (day - pf_day) // 7 + 1
    col = _bloom_column(bloom_week, bloom_feed_weeks)
    return PhaseInfo("bloom", f"{LABELS['bloom']} W{bloom_week}", bloom_week=bloom_week,
                     schedule_stage=f"bloom_{col}", **base)
