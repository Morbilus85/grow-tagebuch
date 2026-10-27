"""Licht: PPFD aus Kalibrierung, DLI, Empfehlungen."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable, Optional

# Richtwerte (editierbar über Settings in einer späteren Version)
TARGETS = {
    "seedling": {"ppfd": (200, 300), "dli_max": 20},
    "veg": {"ppfd": (300, 600), "dli_max": 40},
    "bloom": {"ppfd": (600, 900), "dli_max": 50},
    "flush": {"ppfd": (600, 900), "dli_max": 50},
}


def dli(ppfd: float, hours: float) -> float:
    return round(ppfd * hours * 3600 / 1_000_000, 1)


def _linfit(xs, ys):
    n = len(xs)
    if n == 1:
        return 0.0, ys[0]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0
    return b, my - b * mx


class LightModel:
    """PPFD-Modell aus Messpunkten in der Zeltmitte (Punkt A).

    Pro gemessenem Abstand wird PPFD linear über die Stufe angepasst; zwischen Abständen
    wird im log-log-Raum interpoliert (Potenzgesetz), außerhalb mit dem nächsten Exponenten extrapoliert.
    """

    def __init__(self, points: Iterable):
        center = defaultdict(list)
        edges = defaultdict(list)
        for p in points:
            if p.point == "A":
                center[p.distance_cm].append((p.level, p.ppfd))
            else:
                edges[(p.distance_cm, p.level)].append(p.ppfd)
        self.fits = {}
        for d, vals in center.items():
            xs, ys = zip(*sorted(vals))
            self.fits[d] = _linfit(list(xs), list(ys))
        self.distances = sorted(self.fits)
        self.levels_measured = sorted({lv for vals in center.values() for lv, _ in vals})
        # Randfaktor: Mittel der Randpunkte / Mitte bei gleicher Einstellung
        ratios = []
        for (d, lv), vals in edges.items():
            c = self._at_distance(d, lv)
            if c:
                ratios.append(sum(vals) / len(vals) / c)
        self.edge_factor = round(sum(ratios) / len(ratios), 2) if ratios else None

    @property
    def calibrated(self) -> bool:
        return bool(self.fits)

    def _at_distance(self, d: int, level: float) -> float:
        b, a = self.fits[d]
        return max(a + b * level, 0.0)

    def ppfd(self, level: float, distance: float) -> Optional[float]:
        if not self.fits:
            return None
        ds = self.distances
        if len(ds) == 1:
            return round(self._at_distance(ds[0], level), 0)
        if distance <= ds[0]:
            d1, d2 = ds[0], ds[1]
        elif distance >= ds[-1]:
            d1, d2 = ds[-2], ds[-1]
        else:
            d1 = max(d for d in ds if d <= distance)
            d2 = min(d for d in ds if d >= distance)
            if d1 == d2:
                return round(self._at_distance(d1, level), 0)
        p1, p2 = self._at_distance(d1, level), self._at_distance(d2, level)
        if p1 <= 0 or p2 <= 0:
            return 0.0
        k = math.log(p1 / p2) / math.log(d2 / d1)
        return round(p1 * (d1 / distance) ** k, 0)

    def is_extrapolated(self, level: float, distance: float) -> bool:
        return (level < min(self.levels_measured) or level > max(self.levels_measured)
                or distance < self.distances[0] or distance > self.distances[-1])

    def recommend(self, phase: str, hours: float, max_distance: Optional[float] = None, limit: int = 3):
        t = TARGETS.get(phase)
        if not t or not self.fits:
            return []
        lo, hi = t["ppfd"]
        top = int(max_distance) if max_distance else 70
        out = []
        for dist in range(25, max(top, 25) + 1, 5):
            for lv in range(1, 11):
                p = self.ppfd(lv, dist)
                if p is None or not (lo <= p <= hi):
                    continue
                dl = dli(p, hours)
                if dl > t["dli_max"]:
                    continue
                out.append({"distance_cm": dist, "level": lv, "ppfd": p, "dli": dl,
                            "extrapolated": self.is_extrapolated(lv, dist)})
        # Bevorzugt: gemessener Bereich, größerer Abstand (gleichmäßiger), mittlere PPFD im Zielband
        mid = (lo + hi) / 2
        out.sort(key=lambda r: (r["extrapolated"], -r["distance_cm"], abs(r["ppfd"] - mid)))
        seen, res = set(), []
        for r in out:
            if r["distance_cm"] in seen:
                continue
            seen.add(r["distance_cm"])
            res.append(r)
            if len(res) >= limit:
                break
        return res


def assess(model: LightModel, phase: str, level: Optional[int], distance: Optional[float], hours: float) -> dict:
    """Bewertet die aktuelle Einstellung."""
    res = {"ppfd": None, "dli": None, "status": "unbekannt", "messages": []}
    if not model.calibrated or level is None or distance is None:
        res["messages"].append("Lichtstufe und Abstand im Run eintragen, dann wird PPFD/DLI berechnet.")
        return res
    p = model.ppfd(level, distance)
    res["ppfd"], res["dli"] = p, dli(p, hours)
    if model.edge_factor:
        res["ppfd_edge"] = round(p * model.edge_factor, 0)
    t = TARGETS.get(phase)
    if not t:
        res["status"] = "ok"
        return res
    lo, hi = t["ppfd"]
    status = "ok"
    if res["dli"] > t["dli_max"]:
        status = "zu_hoch"
        res["messages"].append(f"DLI {res['dli']} über Richtwert {t['dli_max']} für diese Phase – Stufe senken oder Lampe höher.")
    if p > hi * 1.1:
        status = "zu_hoch"
        res["messages"].append(f"PPFD {p:.0f} über Zielbereich {lo}–{hi}.")
    elif p < lo * 0.9:
        status = "zu_niedrig" if status == "ok" else status
        res["messages"].append(f"PPFD {p:.0f} unter Zielbereich {lo}–{hi}.")
    res["status"] = status
    res["target"] = {"ppfd": t["ppfd"], "dli_max": t["dli_max"]}
    return res
