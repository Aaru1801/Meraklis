"""Ingest neighbourhood-safety context from Toronto's Community Safety Indicators.

The crime dataset (Major Crime Indicators: Assault, Break & Enter, Auto Theft,
Robbery, Theft Over) carries a neighbourhood (of Toronto's 158) and lat/lng for
~99% of ~475k events. RentSafeTO buildings carry a *ward*, not a neighbourhood,
so we:

  1. Aggregate recent crimes (last 3 full years) per neighbourhood, by category.
  2. Map each building → its neighbourhood by the modal neighbourhood of nearby
     crimes (a coarse spatial grid — self-contained, no boundary file needed).
  3. Rank the 158 neighbourhoods by total reported volume → a relative safety
     percentile (higher = fewer reported incidents = safer-by-this-measure).

This is **area context**, not a judgment of a building or its residents, and it
**never affects the deterministic risk score**. The heavy CSV is processed once;
only a tiny ``building_safety`` table (one row per building) is committed.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_safety \
        --csv "~/Downloads/Community Safety Indicators.csv"
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict

from ..data.store import DEFAULT_DB_PATH

YEARS = {"2023", "2024", "2025"}  # last 3 full years (2026 is partial)
VIOLENT = {"Assault", "Robbery"}
PROPERTY = {"Break and Enter", "Auto Theft", "Theft Over"}
CELL = 2  # lat/lng rounding for the assignment grid (~1.1 km cells)


def _cell(lat: float, lng: float) -> tuple[float, float]:
    return (round(lat, CELL), round(lng, CELL))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="~/Downloads/Community Safety Indicators.csv")
    args = ap.parse_args()
    path = os.path.expanduser(args.csv)
    if not os.path.exists(path):
        sys.exit(f"CSV not found: {path}")

    # per-neighbourhood aggregation + a coarse grid (cell -> hood counts) for
    # mapping buildings to a neighbourhood.
    hood_total: Counter[str] = Counter()
    hood_violent: Counter[str] = Counter()
    hood_property: Counter[str] = Counter()
    hood_cats: dict[str, Counter[str]] = defaultdict(Counter)
    grid: dict[tuple[float, float], Counter[str]] = defaultdict(Counter)

    print(f"Reading {path} …")
    n = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("OCC_YEAR") not in YEARS:
                continue
            hood = (row.get("NEIGHBOURHOOD_158") or "").strip()
            if not hood or hood == "NSA":
                continue
            cat = (row.get("CSI_CATEGORY") or "").strip()
            hood_total[hood] += 1
            hood_cats[hood][cat] += 1
            if cat in VIOLENT:
                hood_violent[hood] += 1
            elif cat in PROPERTY:
                hood_property[hood] += 1
            try:
                lat = float(row["LAT_WGS84"]); lng = float(row["LONG_WGS84"])
                grid[_cell(lat, lng)][hood] += 1
            except (ValueError, KeyError, TypeError):
                pass
            n += 1
            if n % 100_000 == 0:
                print(f"  {n:,} recent crimes…")
    print(f"  {n:,} recent crimes across {len(hood_total)} neighbourhoods.")

    # Relative safety percentile per neighbourhood (fewer crimes = safer = higher).
    ranked = sorted(hood_total, key=lambda h: hood_total[h])  # ascending = safest first
    m = len(ranked)
    pct = {h: round(100 * (m - 1 - i) / (m - 1)) if m > 1 else 50 for i, h in enumerate(ranked)}

    def assign(lat: float, lng: float) -> str | None:
        cl, cn = round(lat, CELL), round(lng, CELL)
        step = 10 ** -CELL
        for r in range(0, 4):  # expand the search box until we find crimes
            agg: Counter[str] = Counter()
            for i in range(-r, r + 1):
                for j in range(-r, r + 1):
                    agg.update(grid.get((round(cl + i * step, CELL), round(cn + j * step, CELL)), {}))
            if agg:
                return agg.most_common(1)[0][0]
        return None

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS building_safety (
            rsn TEXT PRIMARY KEY,
            neighbourhood TEXT,
            crimes_3y INTEGER,
            violent_3y INTEGER,
            property_3y INTEGER,
            safety_percentile INTEGER,
            top_categories_json TEXT
        )
        """
    )
    conn.execute("DELETE FROM building_safety")

    rows = []
    assigned = 0
    for rsn, lat, lng in conn.execute(
        "SELECT rsn, latitude, longitude FROM buildings WHERE latitude IS NOT NULL"
    ).fetchall():
        hood = assign(lat, lng)
        if not hood:
            continue
        assigned += 1
        top = [{"category": c, "count": n} for c, n in hood_cats[hood].most_common(5)]
        rows.append((
            rsn, hood, hood_total[hood], hood_violent[hood], hood_property[hood],
            pct[hood], json.dumps(top),
        ))
    conn.executemany(
        "INSERT OR REPLACE INTO building_safety "
        "(rsn, neighbourhood, crimes_3y, violent_3y, property_3y, safety_percentile, top_categories_json) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    n_b = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
    conn.close()

    print("\nDone. Neighbourhood safety:")
    print(f"  neighbourhoods ranked : {m}")
    print(f"  buildings assigned    : {assigned:,} / {n_b:,}")
    safest = ranked[0]
    worst = ranked[-1]
    print(f"  safest hood           : {safest} ({hood_total[safest]:,} crimes/3y, pct {pct[safest]})")
    print(f"  highest-volume hood   : {worst} ({hood_total[worst]:,} crimes/3y, pct {pct[worst]})")


if __name__ == "__main__":
    main()
