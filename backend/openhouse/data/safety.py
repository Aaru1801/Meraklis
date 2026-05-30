"""Neighbourhood-safety context lookups over the ``building_safety`` cache.

Reads the small per-building table produced by ``ingest_safety`` and frames it as
*area context*. Degrades to None if the table is absent. Never affects the risk
score; it's a separate, clearly-labelled neighbourhood signal.
"""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache

from pydantic import BaseModel, Field

from .store import DEFAULT_DB_PATH


class CrimeCategory(BaseModel):
    category: str
    count: int


class NeighbourhoodSafety(BaseModel):
    available: bool = True
    neighbourhood: str = ""
    crimes_3y: int = 0
    violent_3y: int = 0
    property_3y: int = 0
    per_year: int = 0
    safety_percentile: int = 50  # higher = safer (fewer reported incidents)
    band: str = "moderate"  # safer | moderate | higher
    top_categories: list[CrimeCategory] = Field(default_factory=list)
    summary: str = ""
    basis: str = (
        "Toronto Police Service Major Crime Indicators (Assault, Break & Enter, Auto "
        "Theft, Robbery, Theft Over), last 3 full years, aggregated by neighbourhood."
    )
    disclaimer: str = (
        "Reported-incident context for the surrounding neighbourhood — area context only, "
        "not a measure of this building or its residents, and it never affects the risk score."
    )


@lru_cache(maxsize=1)
def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _has_table() -> bool:
    return (
        _conn().execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='building_safety'"
        ).fetchone()
        is not None
    )


def _band(pct: int) -> tuple[str, str]:
    if pct >= 66:
        return "safer", "among the safer areas in the city"
    if pct >= 33:
        return "moderate", "around the middle of the city"
    return "higher", "a higher-crime area relative to the city"


def safety_for(rsn: str) -> NeighbourhoodSafety | None:
    """Neighbourhood-safety context for a building, or None if unavailable."""
    if not _has_table():
        return None
    row = _conn().execute(
        "SELECT neighbourhood, crimes_3y, violent_3y, property_3y, safety_percentile, "
        "top_categories_json FROM building_safety WHERE rsn = ?",
        (rsn,),
    ).fetchone()
    if not row:
        return None
    pct = int(row["safety_percentile"])
    band, phrase = _band(pct)
    per_year = round(row["crimes_3y"] / 3)
    cats = [CrimeCategory(**c) for c in json.loads(row["top_categories_json"] or "[]")]
    summary = (
        f"{row['neighbourhood']} records about {per_year:,} reported major crimes a year "
        f"(last 3 years) — {phrase} (safety percentile {pct}/100). "
        f"Most common: {cats[0].category}." if cats else
        f"{row['neighbourhood']} records about {per_year:,} reported major crimes a year."
    )
    return NeighbourhoodSafety(
        available=True,
        neighbourhood=row["neighbourhood"],
        crimes_3y=row["crimes_3y"],
        violent_3y=row["violent_3y"],
        property_3y=row["property_3y"],
        per_year=per_year,
        safety_percentile=pct,
        band=band,
        top_categories=cats,
        summary=summary,
    )
