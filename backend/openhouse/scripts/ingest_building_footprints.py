"""Build a GeoJSON of our buildings' real footprints for the MapLibre 3D map.

The City 3D-Massing *Shapefile* has 428k building footprints (PolygonZ, EPSG:3857)
with MIN/MAX/AVG height and the building's true LONGITUDE/LATITUDE as attributes.
We match each RentSafeTO building (by lat/lng) to its nearest footprint and emit a
small GeoJSON FeatureCollection (footprint polygon in WGS84 lng/lat + risk props +
real height). MapLibre renders it as a risk-coloured ``fill-extrusion`` at the
correct location/size; the all-city grey buildings come from the vector basemap.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_building_footprints \
        --shp TorontoBuildingModels/_fp/3DMassingShapefile_2025_WGS84.shp
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

import shapefile  # pyshp

from ..agents.service import _risk_band_for_score
from ..data.store import DEFAULT_DB_PATH
from ..risk import grade_for

R = 6378137.0
MATCH_RADIUS_M = 60.0
GRID = 0.0012  # ~130 m lat cells
_OUT = Path(__file__).resolve().parents[3] / "frontend" / "public" / "buildings.geojson"


def merc_to_lnglat(x: float, y: float) -> tuple[float, float]:
    return (
        x / R * 180.0 / math.pi,
        (2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * 180.0 / math.pi,
    )


def _dist_m(lat1, lng1, lat2, lng2) -> float:
    dx = (lng2 - lng1) * math.cos(math.radians(lat1)) * 111320.0
    dy = (lat2 - lat1) * 110540.0
    return math.hypot(dx, dy)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp", default="TorontoBuildingModels/_fp/3DMassingShapefile_2025_WGS84.shp")
    args = ap.parse_args()

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT rsn, address, ward_name, latitude, longitude, units, storeys, score "
        "FROM buildings WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    ).fetchall()
    conn.close()
    buildings = [dict(r) for r in rows]
    print(f"buildings to match: {len(buildings)}")

    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, b in enumerate(buildings):
        grid[(round(b["latitude"] / GRID), round(b["longitude"] / GRID))].append(i)

    # best footprint per building index -> (dist, ring_pts_3857, height_m)
    best: dict[int, tuple[float, list, float]] = {}
    sf = shapefile.Reader(args.shp)
    fields = [f[0] for f in sf.fields[1:]]
    fi = {name: k for k, name in enumerate(fields)}
    seen = 0
    for sr in sf.iterShapeRecords():
        rec = sr.record
        lng, lat = rec[fi["LONGITUDE"]], rec[fi["LATITUDE"]]
        if lng is None or lat is None:
            continue
        ci, cj = round(lat / GRID), round(lng / GRID)
        cand = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for bi in grid.get((ci + di, cj + dj), ()):
                    b = buildings[bi]
                    d = _dist_m(lat, lng, b["latitude"], b["longitude"])
                    if d > MATCH_RADIUS_M or (bi in best and best[bi][0] <= d):
                        continue
                    if cand is None:
                        pts = sr.shape.points
                        parts = list(sr.shape.parts) + [len(pts)]
                        # exterior ring = first part
                        ring = pts[parts[0]:parts[1]]
                        h = rec[fi["MAX_HEIGHT"]] or rec[fi["AVG_HEIGHT"]] or 0.0
                        cand = (ring, float(h or 0.0))
                    best[bi] = (d, cand[0], cand[1])
        seen += 1
        if seen % 80000 == 0:
            print(f"  …{seen:,} footprints scanned, {len(best)} matched")

    features = []
    for bi, (_d, ring, h) in best.items():
        b = buildings[bi]
        coords = [list(merc_to_lnglat(x, y)) for (x, y) in ring]
        if len(coords) < 4:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])  # close the ring
        score = b["score"]
        height = h if h and h > 2 else (b["storeys"] or 3) * 3.1
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {
                "rsn": b["rsn"], "address": b["address"], "ward": b["ward_name"],
                "score": score, "grade": grade_for(score),
                "risk": _risk_band_for_score(score),
                "storeys": b["storeys"], "units": b["units"],
                "height": round(height, 1),
            },
        })

    _OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    mb = _OUT.stat().st_size / 1e6
    print("\nDone. Building footprints GeoJSON:")
    print(f"  matched : {len(features):,} / {len(buildings):,} ({round(100*len(features)/len(buildings))}%)")
    print(f"  size    : {mb:.1f} MB  ({_OUT})")


if __name__ == "__main__":
    main()
