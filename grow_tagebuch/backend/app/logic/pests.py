"""Bewertet Behandlungen nach Phase der betroffenen Pflanzen."""
from __future__ import annotations

from typing import Optional

from ..pest_data import PESTS

PEST = {p["key"]: p for p in PESTS}
PHASE_ORDER = {"geplant": 0, "einweichen": 0, "keimung": 1, "seedling": 1, "veg": 2, "bloom": 3, "flush": 4, "harvest": 5}
PHASE_LABEL = {"seedling": "Sämling", "veg": "Wachstum", "bloom": "Blüte", "flush": "Reife"}


def normalize_phase(phase: str) -> str:
    return {"geplant": "seedling", "einweichen": "seedling", "keimung": "seedling", "harvest": "flush"}.get(phase, phase)


def evaluate(treatment: dict, phase: Optional[str], bloom_week: Optional[int]) -> dict:
    ph = normalize_phase(phase or "seedling")
    allowed = ph in treatment["phases"]
    reason = None
    if not allowed:
        later = max(PHASE_ORDER[p] for p in treatment["phases"]) < PHASE_ORDER.get(ph, 0)
        reason = (f"In der Phase {PHASE_LABEL.get(ph, ph)} nicht mehr erlaubt." if later
                  else f"Erst ab Phase {PHASE_LABEL.get(treatment['phases'][0], treatment['phases'][0])}.")
    elif ph == "bloom" and treatment.get("bloom_week_max") and bloom_week and bloom_week > treatment["bloom_week_max"]:
        allowed = False
        reason = f"In der Blüte nur bis Woche {treatment['bloom_week_max']}."
    return {**treatment, "allowed": allowed, "blocked_reason": reason}
