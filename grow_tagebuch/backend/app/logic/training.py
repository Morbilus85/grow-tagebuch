"""Bewertet, welche Trainingstechnik für eine Pflanze gerade passt."""
from __future__ import annotations

from datetime import date
from typing import Optional

PHASE_ORDER = {"geplant": 0, "einweichen": 0, "keimung": 0, "seedling": 1, "veg": 2, "bloom": 3, "flush": 4,
               "harvest": 5, "geerntet": 6}
STATUS_ORDER = {"jetzt": 0, "warten": 1, "bald": 2, "vorbei": 3, "nicht_empfohlen": 4}
STATUS_LABEL = {"jetzt": "Jetzt möglich", "warten": "Erholung abwarten", "bald": "Noch nicht",
                "vorbei": "Zeitfenster vorbei", "nicht_empfohlen": "Nicht empfohlen"}


def evaluate(t, *, auto: bool, phase: str, day: Optional[int], bloom_week: Optional[int], nodes: Optional[int],
             last_stress: Optional[tuple[date, int, str]], space_status: str = "ok",
             today: Optional[date] = None) -> dict:
    """t: TrainingTechnique; last_stress: (Datum, Erholungstage, Name) der letzten belastenden Maßnahme."""
    today = today or date.today()
    w = t.window or {}
    suit = t.auto if auto else t.photo
    res = {"key": t.key, "name": t.name, "category": t.category, "stress": t.stress, "suitability": suit,
           "status": "jetzt", "reasons": [], "priority": False}

    def out(status, reason=None):
        res["status"] = status
        if reason:
            res["reasons"].append(reason)
        res["status_label"] = STATUS_LABEL[status]
        return res

    if suit == "abraten":
        return out("nicht_empfohlen", "Für Autos ungeeignet." if auto else "Für Photos nicht empfohlen.")

    if w.get("plan_only"):
        return out("vorbei", "Anbaumethode – wird vor dem Start eines Durchgangs geplant.")

    po = PHASE_ORDER.get(phase, 0)
    allowed = [PHASE_ORDER[p] for p in w.get("phases", ["veg"])]
    if po < min(allowed):
        return out("bald", "Erst ab der Phase " + ("Sämling" if min(allowed) == 1 else "Wachstum" if min(allowed) == 2 else "Blüte") + ".")
    if po > max(allowed):
        return out("vorbei", "Für die aktuelle Phase zu spät.")
    if po not in allowed:
        return out("bald" if po < max(allowed) else "vorbei", "Passt nicht zur aktuellen Phase.")

    if w.get("min_day") and day is not None and day < w["min_day"]:
        return out("bald", f"Frühestens ab etwa Tag {w['min_day']} (heute Tag {day}).")
    if w.get("min_nodes"):
        if nodes is None:
            res["reasons"].append(f"Ab {w['min_nodes']} Nodien – bitte Nodien zählen und unter „Höhe“ eintragen.")
        elif nodes < w["min_nodes"]:
            return out("bald", f"Erst ab {w['min_nodes']} Nodien (aktuell {nodes}).")
    if auto and w.get("auto_max_day") and day is not None and day > w["auto_max_day"]:
        return out("vorbei", f"Bei Autos nur bis etwa Tag {w['auto_max_day']} (heute Tag {day}).")
    if phase == "bloom" and w.get("bloom_week_max") and bloom_week and bloom_week > w["bloom_week_max"]:
        return out("vorbei", f"In der Blüte nur bis Woche {w['bloom_week_max']}.")

    if last_stress and t.category in ("hst", "schnitt") and t.stress in ("mittel", "hoch"):
        d, rec, name = last_stress
        left = rec - (today - d).days
        if left > 0:
            ago = (today - d).days
            when = "heute" if ago == 0 else "gestern" if ago == 1 else f"vor {ago} Tagen"
            return out("warten", f"{name} {when} – noch etwa {left} Tage Erholung, Stress nicht stapeln.")

    if w.get("target_bloom_weeks") and phase == "bloom" and bloom_week in w["target_bloom_weeks"]:
        res["priority"] = True
        res["reasons"].append(f"Typischer Zeitpunkt: Blüte Woche {bloom_week}.")
    if w.get("at_preflower") and phase == "veg" and day and day >= 21:
        res["reasons"].append("Bevorzugt kurz vor bzw. bei Blütebeginn." if not auto else "Bevorzugt rund um die Vorblüte.")
    if t.height_control and space_status in ("knapp", "kritisch"):
        res["priority"] = True
        res["reasons"].append("Hilft gegen den knappen Platz zur Lampe.")
    if suit == "bedingt":
        res["reasons"].append("Nur bedingt geeignet – Hinweise beachten.")
    return out("jetzt")


def rank(results: list[dict]) -> list[dict]:
    return sorted(results, key=lambda r: (STATUS_ORDER[r["status"]], not r["priority"],
                                          {"empfohlen": 0, "bedingt": 1, "abraten": 2}[r["suitability"]]))
