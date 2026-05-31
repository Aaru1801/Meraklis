"""Toronto schools — proximity lookup for family-tailored guidance.

When a renter's profile has children, nearby schools are surfaced as a positive
family factor in the Advocate's guidance. Data: City of Toronto "School locations
— all types" open data (~1,173 points), trimmed to name/type/address/lat/lng in
``schools.json`` (committed alongside this module).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

_SCHOOLS_PATH = Path(__file__).resolve().parent / "schools.json"


@lru_cache(maxsize=1)
def _schools() -> list[dict]:
    try:
        return json.loads(_SCHOOLS_PATH.read_text())
    except Exception:  # noqa: BLE001 - missing/corrupt data should never break the app
        return []


def _dist_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Equirectangular metres — accurate enough at city scale, cheap to compute."""
    dx = (lng2 - lng1) * math.cos(math.radians(lat1)) * 111320.0
    dy = (lat2 - lat1) * 110540.0
    return math.hypot(dx, dy)


def nearest_schools(lat: float, lng: float, n: int = 5, radius_m: float = 1500.0) -> list[dict]:
    """The closest schools to a point, nearest first, within ``radius_m``.

    Each item: ``{name, type, address, lat, lng, distance_m}``.
    """
    out: list[dict] = []
    for s in _schools():
        d = _dist_m(lat, lng, s["lat"], s["lng"])
        if d <= radius_m:
            out.append({**s, "distance_m": round(d)})
    out.sort(key=lambda s: s["distance_m"])
    return out[:n]
