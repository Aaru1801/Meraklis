"""Transparent rent-estimation model (the 'money' layer).

Realtor.ca / HouseSigma have no public API and prohibit scraping, so OpenHouse
does not pull live asking rents. Instead this module produces a *transparent,
explainable* monthly-rent **estimate** for a building from signals we already
have — distance to downtown (from the building's lat/long), age, and size —
anchored to published Toronto average market rents.

It is clearly labelled an estimate everywhere it surfaces (never presented as a
live listing). If a licensed listing feed (e.g. a CREA DDF® export) is dropped
into the cache, the Realtor adapter uses that real data instead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Downtown Toronto (Union/Financial District) — the price gravity centre.
_DOWNTOWN = (43.6532, -79.3832)

# Blended "typical unit" asking-rent anchor for Toronto (modeled from CMHC /
# market-rent averages). Adjusted per building below.
_CITY_BASE_RENT = 2100


def _km_from_downtown(lat: float, lng: float) -> float:
    """Approximate straight-line distance (km) from downtown — fine at city scale."""
    dlat = math.radians(lat - _DOWNTOWN[0])
    dlng = math.radians(lng - _DOWNTOWN[1])
    mean_lat = math.radians((lat + _DOWNTOWN[0]) / 2)
    x = dlng * math.cos(mean_lat)
    return math.hypot(x, dlat) * 6371.0


def _location_multiplier(lat: float, lng: float) -> float:
    d = _km_from_downtown(lat, lng)
    return max(0.82, min(1.30, 1.28 - 0.03 * d))


def _age_multiplier(year_built: int | None) -> float:
    if not year_built:
        return 1.0
    if year_built >= 2015:
        return 1.30
    if year_built >= 2000:
        return 1.12
    if year_built >= 1980:
        return 1.0
    if year_built >= 1965:
        return 0.92
    return 0.85


def _round25(x: float) -> int:
    return int(round(x / 25.0) * 25)


@dataclass(frozen=True, slots=True)
class RentEstimate:
    monthly: int
    low: int
    high: int
    confidence: float
    basis: str
    is_estimate: bool = True


def estimate_rent(
    latitude: float | None,
    longitude: float | None,
    year_built: int | None = None,
    units: int | None = None,
    storeys: int | None = None,
) -> RentEstimate | None:
    """Estimate a typical monthly asking rent for a building. None if not locatable."""
    if latitude is None or longitude is None:
        return None
    d = _km_from_downtown(latitude, longitude)
    loc = _location_multiplier(latitude, longitude)
    age = _age_multiplier(year_built)
    monthly = _round25(_CITY_BASE_RENT * loc * age)
    low = _round25(monthly * 0.90)
    high = _round25(monthly * 1.12)
    basis = (
        f"Modeled estimate from Toronto average market rents, adjusted for "
        f"~{d:.0f} km from downtown and a building "
        f"{'built ' + str(year_built) if year_built else 'of unknown age'}. "
        "Not a live listing."
    )
    return RentEstimate(monthly=monthly, low=low, high=high, confidence=0.4, basis=basis)
