"""Nur lesender Zugriff auf Home Assistant (über die Supervisor-API im Add-on)."""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

log = logging.getLogger("grow.ha")

_TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HA_TOKEN")
_BASE = os.environ.get("HA_URL", "http://supervisor/core") + "/api"


def available() -> bool:
    return bool(_TOKEN)


async def get_states(entity_ids: list[str]) -> dict[str, dict]:
    """Liefert {entity_id: state-objekt}. Fehlende/fehlerhafte Entitäten fehlen im Ergebnis."""
    if not _TOKEN or not entity_ids:
        return {}
    out = {}
    headers = {"Authorization": f"Bearer {_TOKEN}"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        for eid in entity_ids:
            try:
                r = await client.get(f"{_BASE}/states/{eid}")
                if r.status_code == 200:
                    out[eid] = r.json()
            except httpx.HTTPError as e:
                log.warning("HA-Abfrage %s fehlgeschlagen: %s", eid, e)
    return out


def num(state: Optional[dict]) -> Optional[float]:
    """Zahlenwert einer Entität. Lampen (light.*) liefern die Helligkeit in %, Lüfter (fan.*) die Drehzahl in %."""
    if not state:
        return None
    eid = state.get("entity_id") or ""
    if eid.startswith(("light.", "fan.")):
        st = state.get("state")
        if st == "off":
            return 0.0
        if st != "on":
            return None
        a = state.get("attributes") or {}
        if eid.startswith("fan."):
            return float(a["percentage"]) if a.get("percentage") is not None else None
        return round(a["brightness"] * 100 / 255) if a.get("brightness") is not None else 100.0
    try:
        return float(state.get("state"))
    except (TypeError, ValueError):
        return None


def on(state: Optional[dict]) -> Optional[bool]:
    if not state or state.get("state") in ("unknown", "unavailable", None):
        return None
    return state.get("state") == "on"
