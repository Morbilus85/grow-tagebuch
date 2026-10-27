"""Platz im Zelt: erreichbarer Lampenabstand und Höhenprognose."""
from __future__ import annotations

from datetime import date
from typing import Optional

MIN_USEFUL_DISTANCE = 30  # cm – darunter wird es bei dieser Lampe schnell zu viel Licht/Hitze


def headroom(tent_height: Optional[int], lamp_hang: int, pot_height: int, plant_height: Optional[float]) -> Optional[float]:
    """Maximal möglicher Abstand Lampe -> Pflanzenspitze, wenn die Lampe ganz oben hängt."""
    if not tent_height or plant_height is None:
        return None
    return round(tent_height - lamp_hang - pot_height - plant_height, 0)


def assess(tent_height, lamp_hang, pot_height, heights: list[tuple[date, float]], recommended_min: Optional[float],
           auto: bool, week: Optional[int], max_strain_height: Optional[int]) -> dict:
    """heights: (Datum, Höhe cm), aufsteigend sortiert."""
    res = {"height_cm": None, "max_distance_cm": None, "growth_cm_per_day": None, "days_until_tight": None,
           "messages": [], "status": "ok"}
    if not heights:
        if auto and week and week >= 3:
            res["messages"].append("Höhe messen – ab Woche 3 wird LST für Autos wichtig.")
        return res
    h = heights[-1][1]
    res["height_cm"] = h
    room = headroom(tent_height, lamp_hang, pot_height, h)
    res["max_distance_cm"] = room
    if len(heights) >= 2:
        (d1, h1), (d2, h2) = heights[-2], heights[-1]
        days = (d2 - d1).days
        if days > 0 and h2 > h1:
            rate = (h2 - h1) / days
            res["growth_cm_per_day"] = round(rate, 1)
            need = max(recommended_min or MIN_USEFUL_DISTANCE, MIN_USEFUL_DISTANCE)
            if room is not None and room > need:
                res["days_until_tight"] = int((room - need) / rate)
    if room is not None:
        if room < MIN_USEFUL_DISTANCE:
            res["status"] = "kritisch"
            res["messages"].append(f"Nur noch {room:.0f} cm bis zur Lampe möglich – sofort herunterbinden (LST) und Lichtstufe senken.")
        elif recommended_min and room < recommended_min:
            res["status"] = "knapp"
            res["messages"].append(f"Empfohlener Abstand {recommended_min:.0f} cm ist nicht mehr erreichbar (max. {room:.0f} cm) – LST oder niedrigere Stufe.")
        elif res["days_until_tight"] is not None and res["days_until_tight"] <= 10:
            res["status"] = "knapp"
            res["messages"].append(f"Bei aktuellem Wachstum wird es in ca. {res['days_until_tight']} Tagen eng – LST jetzt beginnen.")
    if auto and week and 3 <= week <= 5 and max_strain_height and tent_height and max_strain_height > (tent_height - lamp_hang - pot_height - MIN_USEFUL_DISTANCE):
        res["messages"].append(f"Sorte wird bis ca. {max_strain_height} cm hoch – im Zelt ist Platz für ca. "
                               f"{tent_height - lamp_hang - pot_height - MIN_USEFUL_DISTANCE} cm. LST einplanen (kein Toppen bei Autos).")
    return res
