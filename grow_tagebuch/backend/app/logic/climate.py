"""Klima: VPD-Berechnung, Zielbereiche, Aufzeichnung und Verdichtung."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from .. import ha
from ..models import ClimateSample, SensorMapping

VPD_TARGETS = {
    "seedling": (0.4, 0.8),
    "veg": (0.8, 1.2),
    "bloom": (1.0, 1.5),
    "flush": (1.2, 1.6),
}
TEMP_TARGETS = {
    "seedling": (22, 27),
    "veg": (22, 28),
    "bloom": (20, 27),
    "flush": (18, 26),
}
LEAF_OFFSET = 1.0  # Blatt ca. 1 °C kühler als Luft unter LED (Richtwert)
RAW_KEEP_DAYS = 14


def svp(t: float) -> float:
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def vpd_air(t: Optional[float], rh: Optional[float]) -> Optional[float]:
    if t is None or rh is None:
        return None
    return round(svp(t) * (1 - rh / 100), 2)


def vpd_leaf(t: Optional[float], rh: Optional[float], offset: float = LEAF_OFFSET) -> Optional[float]:
    if t is None or rh is None:
        return None
    return round(svp(t - offset) - svp(t) * rh / 100, 2)


def rate(value: Optional[float], rng: Optional[tuple]) -> str:
    if value is None or not rng:
        return "unbekannt"
    lo, hi = rng
    if lo <= value <= hi:
        return "ok"
    span = hi - lo
    if value < lo - span * 0.5 or value > hi + span * 0.5:
        return "schlecht"
    return "grenzwertig"


def mappings(session: Session, setup_id: int) -> dict[str, str]:
    return {m.role: m.entity_id for m in session.exec(select(SensorMapping).where(SensorMapping.setup_id == setup_id))}


async def read_live(session: Session, setup_id: int) -> dict:
    m = mappings(session, setup_id)
    states = await ha.get_states(list(m.values()))
    g = lambda role: states.get(m.get(role, ""))  # noqa: E731
    t, rh = ha.num(g("temp")), ha.num(g("rh"))
    return {
        "available": ha.available() and bool(states),
        "temp": t,
        "rh": rh,
        "vpd": ha.num(g("vpd")) or vpd_air(t, rh),
        "vpd_leaf": vpd_leaf(t, rh),
        "light_level": ha.num(g("light_level")),
        "light_on": ha.on(g("light_on")),
        "exhaust_level": ha.num(g("exhaust_level")),
        "heater_on": ha.on(g("heater_switch")),
        "heatmat_on": ha.on(g("heatmat_switch")),
        "room_temp": ha.num(g("room_temp")),
        "room_rh": ha.num(g("room_rh")),
        "ts": datetime.now().replace(microsecond=0).isoformat(),
    }


async def sample(session: Session, setup_id: int) -> Optional[ClimateSample]:
    live = await read_live(session, setup_id)
    if not live["available"] or (live["temp"] is None and live["rh"] is None):
        return None
    s = ClimateSample(setup_id=setup_id, ts=datetime.now().replace(second=0, microsecond=0), temp=live["temp"],
                      rh=live["rh"], vpd=live["vpd"], light_level=live["light_level"],
                      heater_on=live["heater_on"], heatmat_on=live["heatmat_on"])
    session.add(s)
    session.commit()
    return s


def aggregate_old(session: Session, keep_days: int = RAW_KEEP_DAYS) -> int:
    """Verdichtet Rohwerte älter als keep_days auf Stundenwerte (Mittel/Min/Max)."""
    cutoff = datetime.now() - timedelta(days=keep_days)
    raw = session.exec(select(ClimateSample).where(ClimateSample.ts < cutoff, ClimateSample.aggregated == False)  # noqa: E712
                       .order_by(ClimateSample.ts)).all()
    buckets: dict[tuple, list[ClimateSample]] = {}
    for s in raw:
        buckets.setdefault((s.setup_id, s.ts.replace(minute=0, second=0)), []).append(s)
    n = 0
    for (setup_id, hour), rows in buckets.items():
        def avg(attr):
            v = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
            return round(sum(v) / len(v), 2) if v else None
        temps = [r.temp for r in rows if r.temp is not None]
        rhs = [r.rh for r in rows if r.rh is not None]
        session.add(ClimateSample(setup_id=setup_id, ts=hour, temp=avg("temp"), rh=avg("rh"), vpd=avg("vpd"),
                                  light_level=avg("light_level"),
                                  temp_min=min(temps) if temps else None, temp_max=max(temps) if temps else None,
                                  rh_min=min(rhs) if rhs else None, rh_max=max(rhs) if rhs else None,
                                  heater_on=any(r.heater_on for r in rows), heatmat_on=any(r.heatmat_on for r in rows),
                                  aggregated=True))
        for r in rows:
            session.delete(r)
        n += 1
    session.commit()
    return n
