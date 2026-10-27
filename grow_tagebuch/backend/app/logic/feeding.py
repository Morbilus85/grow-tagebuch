"""Regelbasierter Gieß- und Düngeassistent (organisch, BioBizz-Basis).

Grundsatz: Das Herstellerschema liefert die Dosis. Regeln dürfen nur weglassen, reduzieren oder warnen –
nie über die Schemadosis bzw. das Etikett-Maximum hinausgehen.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

PH_TARGET = (6.2, 6.8)
TOPDRESS_WINDOW_DAYS = 14
TOPDRESS_FACTOR = 0.75
DUP_WINDOW_DAYS = 7


@dataclass
class PlantCtx:
    plant_id: int
    name: str
    stage: Optional[str]  # seedling, veg, bloom_1..8, flush, None
    phase: str
    bloom_week: Optional[int]
    preflower_confirmed_or_reached: bool
    weeks_in_soil: float
    feed_factor: float = 1.0
    mg_flag: bool = False
    recent_logs: list = field(default_factory=list)  # LogEntry-ähnliche Objekte, neueste zuerst


@dataclass
class Item:
    key: str
    name: str
    unit: str
    per_l: Optional[float]
    total: Optional[float]
    source: str  # schema | regel | extra
    note: str = ""


def _round(x: Optional[float], step: float = 0.1) -> Optional[float]:
    if x is None:
        return None
    return round(round(x / step) * step, 2)


def soil_block_weeks(soil) -> int:
    if not soil:
        return 0
    w = soil.prefertilized_weeks or 0
    if soil.schedule_type == "all_mix" and (soil.worm_humus_pct or 0) >= 10:
        w += 1
    return w


def feed_factor(ctx: PlantCtx, soil, today: date) -> tuple[float, list[str], bool]:
    """Liefert (Faktor für Grunddünger, Begründungen, Grunddünger gesperrt?)."""
    reasons = []
    block = soil_block_weeks(soil)
    blocked = ctx.weeks_in_soil < block
    if blocked:
        reasons.append(f"Erde noch vorgedüngt (Woche {int(ctx.weeks_in_soil) + 1} von {block}) – keine Grunddünger.")
        return 0.0, reasons, True
    weeks_after = ctx.weeks_in_soil - block
    f = min(1.0, 0.5 + 0.25 * int(weeks_after))
    if f < 1.0:
        reasons.append(f"Einstieg nach vorgedüngter Erde: {int(f * 100)} % der Schemadosis.")
    td = [l for l in ctx.recent_logs if l.type == "top_dress" and (today - l.ts.date()).days <= TOPDRESS_WINDOW_DAYS]
    if td:
        f *= TOPDRESS_FACTOR
        reasons.append(f"Top-Dress vor {(today - td[0].ts.date()).days} Tagen – Grunddünger um 25 % reduziert.")
    if ctx.feed_factor != 1.0:
        f *= ctx.feed_factor
        reasons.append(f"Pflanzen-Faktor {ctx.feed_factor:.2f} (manuell).")
    return round(min(f, 1.0), 2), reasons, False


def ph_down_hint(recent_logs) -> Optional[float]:
    vals = [l.ph_down_ml_per_l for l in recent_logs if getattr(l, "ph_down_ml_per_l", None)]
    if not vals:
        return None
    return round(statistics.median(vals[:5]), 2)


def build_recipe(ctx_group: list[PlantCtx], volumes: dict[int, float], schedule: dict[str, float], products: dict,
                 soil, water, today: Optional[date] = None, extras: Optional[list[dict]] = None,
                 lights_on: Optional[bool] = None) -> dict:
    """Ein Kannen-Rezept für eine Gruppe von Pflanzen in derselben Stufe.

    schedule: product_key -> ml/l für die Stufe der Gruppe
    products: product_key -> Product
    extras:   vom Nutzer gewünschte Zusätze [{product_key, per_l, application}]
    """
    today = today or date.today()
    lead = ctx_group[0]
    total_l = round(sum(volumes.get(c.plant_id, 0) for c in ctx_group), 2)
    items: list[Item] = []
    skipped: list[dict] = []
    warnings: list[str] = []
    blocks: list[str] = []
    info: list[str] = []

    stage = lead.stage
    all_logs = sorted({id(l): l for c in ctx_group for l in c.recent_logs}.values(), key=lambda l: l.ts, reverse=True)

    def add(key, per_l, source, note=""):
        p = products.get(key)
        name = p.name if p else key
        unit = p.unit if p else "ml"
        items.append(Item(key, name, unit, _round(per_l), _round(per_l * total_l) if per_l is not None else None, source, note))

    if stage in (None, "flush"):
        info.append("Nur Wasser (Reife/Spülphase)." if stage == "flush" else "Keine Düngung in dieser Phase.")
        schedule = {}

    factor, reasons, base_blocked = feed_factor(lead, soil, today)
    info.extend(reasons)

    for key, dose in sorted(schedule.items()):
        p = products.get(key)
        if stage == "seedling" and (p is None or p.kind != "root"):
            skipped.append({"name": p.name if p else key, "reason": "Sämling: nur Wasser + Wurzelstimulator"})
            continue
        if p is None or not p.in_stock:
            alt = ""
            if key == "biobizz_microbes" and products.get("dimikro_bodenhilfsstoff") and products["dimikro_bodenhilfsstoff"].in_stock:
                alt = " – Ersatz: DiMikro Bodenhilfsstoff nach Etikett"
                d = products["dimikro_bodenhilfsstoff"]
                add(d.key, d.label_dose_min, "regel", "Ersatz für BioBizz Microbes" + ("" if d.label_dose_min else " – Dosis laut Etikett"))
            skipped.append({"name": p.name if p else key, "reason": "nicht im Inventar" + alt})
            continue
        if p.kind == "base":
            if base_blocked:
                skipped.append({"name": p.name, "reason": "Erde noch vorgedüngt"})
                continue
            add(key, dose * factor, "schema", f"Schema {dose} ml/l × {factor:.2f}")
        else:
            # Stimulatoren/Wurzel: Schemadosis, in der Vorgedüngt-Phase halbiert
            f2 = 0.5 if base_blocked and stage != "seedling" else 1.0
            add(key, dose * f2, "schema", f"Schema {dose} ml/l" + (" × 0,5 (vorgedüngte Erde)" if f2 < 1 else ""))

    # CalMag: weiches Wasser, Mg knapp -> ab Blüte oder bei Mg-Mangel
    cm = products.get("biobizz_calmag")
    in_bloom = stage and stage.startswith("bloom")
    if cm and cm.in_stock and stage not in (None, "flush", "seedling") and (in_bloom or any(c.mg_flag for c in ctx_group)):
        if water and (water.mg_mg_l or 99) < 15:
            dose = cm.label_dose_min or (cm.label_dose_max / 2 if cm.label_dose_max else None)
            early = stage in ("bloom_1", "bloom_2") and not any(c.mg_flag for c in ctx_group)
            if dose is not None and early:
                dose = dose / 2
            add(cm.key, dose, "regel",
                ("Weiches Wasser, Mg %.1f mg/l" % water.mg_mg_l) + (" – halbe Dosis zum Einstieg" if early else "")
                + ("" if dose is not None else " – Dosis laut Etikett im Inventar eintragen"))

    # Nutzer-Extras prüfen
    for ex in extras or []:
        key = ex.get("product_key")
        p = products.get(key)
        if not p:
            continue
        app = ex.get("application", "giessen")
        bw = lead.bloom_week or 0
        blocked = None
        if app == "spray":
            if key == "neemoel" and (lead.preflower_confirmed_or_reached or lead.phase in ("bloom", "flush")):
                blocked = "Neemöl-Spray ab Vorblüte gesperrt (setzt sich in den Blüten fest)."
            elif bw >= 3:
                blocked = "Blattspray ab Blüte W3 gesperrt (BioBizz: Blattdüngung nur bis Blüte W2)."
            elif lights_on:
                warnings.append(f"{p.name}: Spray nur kurz vor Licht aus – Tropfen wirken unter LED wie Brenngläser.")
        if key == "brennnesselpulver" and bw >= 2:
            warnings.append("Brennnessel ist stickstofflastig – ab Blüte W2 arbeitet sie gegen Bio-Bloom/Top-Max.")
        if p.kind == "carbs" and not (lead.phase in ("bloom", "flush")):
            warnings.append(f"{p.name}: Kohlenhydrate erst ab Blüte sinnvoll; in Wachstum fördern sie eher Trauermücken/Schimmel.")
        if p.label_dose_max and ex.get("per_l") and ex["per_l"] > p.label_dose_max:
            blocked = f"{p.name}: {ex['per_l']} über Etikett-Maximum {p.label_dose_max}."
        if blocked:
            blocks.append(blocked)
            skipped.append({"name": p.name, "reason": blocked})
            continue
        add(key, ex.get("per_l"), "extra", app)

    # Doppelte Wirkgruppen (im Rezept oder in den letzten 7 Tagen gegeben)
    groups: dict[str, set] = {}
    for it in items:
        g = products[it.key].effect_group if it.key in products else ""
        if g:
            groups.setdefault(g, set()).add(it.name)
    for l in all_logs:
        if (today - l.ts.date()).days > DUP_WINDOW_DAYS:
            continue
        for pu in (l.products or []):
            p = products.get(pu.get("product_key"))
            if p and p.effect_group in groups:
                groups[p.effect_group].add(p.name + " (letzte 7 Tage)")
    for g, names in groups.items():
        base_names = {n.replace(" (letzte 7 Tage)", "") for n in names}
        if len(base_names) > 1:
            warnings.append(f"Gleiche Wirkgruppe „{g}“: {', '.join(sorted(names))} – mehr bringt hier nicht mehr.")

    hint = ph_down_hint(all_logs)
    ph = {"target": PH_TARGET, "tap_ph": water.ph if water else None,
          "bio_down_ml_per_l": hint,
          "note": ("Gelernter Wert aus deinen letzten Messungen." if hint else
                   "Bio-Down tropfenweise zugeben und messen; trage die verbrauchte Menge ein, dann lernt die App mit.")}
    ec = {"tap": water.ec if water else None,
          "note": "Organisch: EC nur als Trend. Leitungswasser-EC ist bereits enthalten."}

    return {
        "stage": stage,
        "phase": lead.phase,
        "plants": [{"id": c.plant_id, "name": c.name, "volume_l": volumes.get(c.plant_id, 0)} for c in ctx_group],
        "total_l": total_l,
        "factor": factor,
        "items": [it.__dict__ for it in items],
        "skipped": skipped,
        "warnings": warnings,
        "blocks": blocks,
        "info": info,
        "ph": ph,
        "ec": ec,
    }
