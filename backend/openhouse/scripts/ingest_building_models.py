"""Extract real 3D building shells for our buildings from the City 3D Massing.

The City's "3D Massing — Multipatch" download is an ESRI File Geodatabase tiled
into ~160 ``Multipatch_<tile>`` layers; each building is a 3D MultiPolygon (real
faces, Z = height in metres) in EPSG:3857, with NO id/address. We only need the
~3,500 RentSafeTO apartment buildings we have data for, so we:

  1. Stream every massing building, compute its centroid (3857 -> lng/lat).
  2. Match each RentSafeTO building (lat/lng) to the nearest massing centroid
     within a small radius (location is the only join key).
  3. Triangulate the matched building's faces, projected into the SAME local
     scene coordinates the 3D map already uses (so it lines up with the basemap),
     with heights kept in true proportion (vertical exaggeration is applied in
     the renderer, not baked in).
  4. Write a compact binary (Float32 triangle positions) + a JSON index keyed by
     RSN. Only this small cache is committed; the 216 MB source stays out of git.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_building_models \
        --gdb TorontoBuildingModels/_work/3DMassingMultipatch_2025_WGS84.gdb
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sqlite3
import sys
from array import array
from collections import defaultdict
from pathlib import Path

import fiona

from ..data.store import DEFAULT_DB_PATH

# Must match frontend/src/components/CityModel.tsx projection.
LAT0, LNG0, SCALE = 43.705, -79.38, 26.0
R = 6378137.0  # Web Mercator sphere radius

MATCH_RADIUS_M = 55.0  # a massing centroid this close to a building is "the same"
GRID = 0.0012  # ~130 m lat cells for the building spatial index

_OUT_DIR = Path(__file__).resolve().parents[3] / "frontend" / "public"


def merc_to_lnglat(x: float, y: float) -> tuple[float, float]:
    lng = x / R * 180.0 / math.pi
    lat = (2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * 180.0 / math.pi
    return lng, lat


def project(lat: float, lng: float) -> tuple[float, float]:
    sx = ((lng - LNG0) * math.cos(math.radians(LAT0)) * 111320.0) / SCALE
    sz = (-(lat - LAT0) * 110540.0) / SCALE
    return sx, sz


def _dist_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dx = (lng2 - lng1) * math.cos(math.radians(lat1)) * 111320.0
    dy = (lat2 - lat1) * 110540.0
    return math.hypot(dx, dy)


def _triangulate(coords) -> list[float]:
    """MultiPolygon Z -> flat list of scene-space triangle vertices (x, y, z)."""
    out: list[float] = []
    for poly in coords:
        if not poly:
            continue
        ring = poly[0]  # outer ring; massing faces have no real holes
        pts = []
        for p in ring:
            lng, lat = merc_to_lnglat(p[0], p[1])
            sx, sz = project(lat, lng)
            y = (p[2] if len(p) > 2 and p[2] is not None else 0.0) / SCALE
            pts.append((sx, y, sz))
        # drop a duplicated closing vertex if present
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        for k in range(1, len(pts) - 1):  # fan triangulation
            out.extend(pts[0]); out.extend(pts[k]); out.extend(pts[k + 1])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--gdb",
        default="TorontoBuildingModels/_work/3DMassingMultipatch_2025_WGS84.gdb",
    )
    args = ap.parse_args()
    gdb = args.gdb

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    buildings = [
        (rsn, lat, lng)
        for rsn, lat, lng in conn.execute(
            "SELECT rsn, latitude, longitude FROM buildings "
            "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        )
    ]
    conn.close()
    print(f"buildings to match: {len(buildings)}")

    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, (_rsn, lat, lng) in enumerate(buildings):
        grid[(round(lat / GRID), round(lng / GRID))].append(i)

    # best match per building index -> (dist_m, triangle floats)
    best: dict[int, tuple[float, list[float]]] = {}

    layers = [l for l in fiona.listlayers(gdb) if l.startswith("Multipatch_")]
    print(f"massing layers: {len(layers)}")
    seen = 0
    for li, layer in enumerate(layers):
        with fiona.open(gdb, layer=layer) as src:
            for feat in src:
                geom = feat.get("geometry")
                coords = geom.get("coordinates") if geom else None
                if not coords:
                    continue
                # centroid from outer-ring vertices (cheap; before triangulating)
                sx = sy = 0.0; n = 0
                for poly in coords:
                    for p in poly[0]:
                        sx += p[0]; sy += p[1]; n += 1
                if not n:
                    continue
                clng, clat = merc_to_lnglat(sx / n, sy / n)
                ci, cj = round(clat / GRID), round(clng / GRID)
                # which nearby buildings would accept this model?
                tris: list[float] | None = None
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        for bi in grid.get((ci + di, cj + dj), ()):
                            _rsn, blat, blng = buildings[bi]
                            d = _dist_m(clat, clng, blat, blng)
                            if d > MATCH_RADIUS_M:
                                continue
                            if bi in best and best[bi][0] <= d:
                                continue
                            if tris is None:
                                tris = _triangulate(coords)
                            if tris:
                                best[bi] = (d, tris)
                seen += 1
        if (li + 1) % 30 == 0:
            print(f"  …{li + 1}/{len(layers)} layers, {seen:,} buildings scanned, {len(best)} matched")

    # assemble positions + index
    floats: list[float] = []
    index = []
    for bi, (_d, tris) in best.items():
        rsn = buildings[bi][0]
        v0 = len(floats) // 3
        floats.extend(tris)
        index.append({"rsn": rsn, "v0": v0, "vn": len(tris) // 3})

    # per-axis bbox for 16-bit quantization (X/Z span ~hundreds, Y ~tens, so
    # quantizing each axis independently keeps full precision on height).
    mn = [1e18, 1e18, 1e18]
    mx = [-1e18, -1e18, -1e18]
    for i in range(0, len(floats), 3):
        for a in range(3):
            v = floats[i + a]
            if v < mn[a]: mn[a] = v
            if v > mx[a]: mx[a] = v
    span = [(mx[a] - mn[a]) or 1.0 for a in range(3)]

    quant = array("H", bytes())
    qs = array("H", [0]) * len(floats)
    for i in range(0, len(floats), 3):
        for a in range(3):
            qs[i + a] = max(0, min(65535, int(round((floats[i + a] - mn[a]) / span[a] * 65535))))
    quant = qs
    if sys.byteorder == "big":
        quant.byteswap()

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    # gzip *content* served under a .bin name (octet-stream) so no server/proxy
    # auto-decodes it via Content-Encoding; the renderer inflates it in JS.
    gz_path = _OUT_DIR / "building-models.bin"
    with gzip.open(gz_path, "wb", compresslevel=7) as f:
        f.write(quant.tobytes())
    meta = {
        "scale": SCALE, "lat0": LAT0, "lng0": LNG0,
        "count": len(index), "n_vertices": len(floats) // 3,
        "quant": {"min": mn, "max": mx},
        "index": sorted(index, key=lambda e: e["v0"]),
    }
    json_path = _OUT_DIR / "building-models.json"
    with open(json_path, "w") as f:
        json.dump(meta, f)

    mb = gz_path.stat().st_size / 1e6
    matched = len(index)
    print("\nDone. 3D building models:")
    print(f"  matched buildings : {matched:,} / {len(buildings):,} ({round(100*matched/len(buildings))}%)")
    print(f"  triangles         : {len(floats)//9:,}")
    print(f"  gzip binary size  : {mb:.1f} MB  ({gz_path})")
    print(f"  index             : {json_path}")


if __name__ == "__main__":
    main()
