"""Extrude downtown Toronto building footprints into a compact 3D model layer.

Most of the city is low-rise (6-12 m), so extruding *all* 428k buildings reads as
a flat cross-section and is heavy. Instead we render only the DOWNTOWN CORE as a
three.js model layer (coplanar over the MapLibre base): every footprint inside a
downtown bbox, extruded to its real height (walls + roof). The 6 buildings that
ship as DETAILED landmark meshes (CN Tower, etc.) are excluded so they don't
double-render as grey prisms.

Output is quantized to 16-bit per axis and gzipped (decoded in the browser), so
~950k triangles ship as a few MB instead of ~70 MB of JSON.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_downtown
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

import shapefile  # pyshp

from .ingest_landmarks import LANDMARKS
from ..data.store import DEFAULT_DB_PATH

R = 6378137.0
# Downtown core: ~Bathurst→Sherbourne, lakeshore→~Wellesley — the dense, tall,
# recognizable skyline. Tighter than "central Toronto" for fidelity + perf.
BBOX = (-79.408, 43.636, -79.358, 43.666)  # minLng, minLat, maxLng, maxLat
LANDMARK_EXCLUDE_M = 95.0  # drop footprints this close to a detailed-landmark centre
_DIR = Path(__file__).resolve().parents[3] / "frontend" / "public"


def merc_to_lnglat(x: float, y: float) -> tuple[float, float]:
    return (
        round(x / R * 180.0 / math.pi, 6),
        round((2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * 180.0 / math.pi, 6),
    )


def _dist_m(lat1, lng1, lat2, lng2) -> float:
    dx = (lng2 - lng1) * math.cos(math.radians(lat1)) * 111320.0
    dy = (lat2 - lat1) * 110540.0
    return math.hypot(dx, dy)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp", default="TorontoBuildingModels/_fp/3DMassingShapefile_2025_WGS84.shp")
    args = ap.parse_args()

    sf = shapefile.Reader(args.shp)
    fi = {n: i for i, n in enumerate([f[0] for f in sf.fields[1:]])}
    mnlng, mnlat, mxlng, mxlat = BBOX
    lms = [(lng, lat) for _n, lng, lat in LANDMARKS]

    # RentSafeTO buildings render as the colour-coded risk overlay; exclude them
    # from the grey context so they aren't covered by it.
    GRID = 0.0005
    rgrid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    for blat, blng in conn.execute(
        "SELECT latitude, longitude FROM buildings WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    ):
        rgrid[(round(blat / GRID), round(blng / GRID))].append((blat, blng))
    conn.close()

    def is_rentsafe(lng: float, lat: float) -> bool:
        ci, cj = round(lat / GRID), round(lng / GRID)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for blat, blng in rgrid.get((ci + di, cj + dj), ()):
                    if _dist_m(lat, lng, blat, blng) < 30.0:
                        return True
        return False

    v: list[float] = []
    n = 0
    for sr in sf.iterShapeRecords():
        rec = sr.record
        lng, lat = rec[fi["LONGITUDE"]], rec[fi["LATITUDE"]]
        if lng is None or lat is None or not (mnlng <= lng <= mxlng and mnlat <= lat <= mxlat):
            continue
        if any(_dist_m(lat, lng, ll, lo) < LANDMARK_EXCLUDE_M for (lo, ll) in lms):
            continue  # rendered as a detailed landmark instead
        if is_rentsafe(lng, lat):
            continue  # rendered as the colour-coded risk overlay
        h = rec[fi["MAX_HEIGHT"]] or rec[fi["AVG_HEIGHT"]] or 0.0
        h = float(h or 0.0)
        if h < 2:
            h = 6.0
        shp = sr.shape
        if not shp.points:
            continue
        parts = list(shp.parts) + [len(shp.points)]
        ring = [merc_to_lnglat(x, y) for (x, y) in shp.points[parts[0]:parts[1]]]
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) < 3:
            continue
        m = len(ring)
        for i in range(m):  # walls
            a = ring[i]; b = ring[(i + 1) % m]
            v += [a[0], a[1], 0, b[0], b[1], 0, b[0], b[1], h]
            v += [a[0], a[1], 0, b[0], b[1], h, a[0], a[1], h]
        for k in range(1, m - 1):  # roof
            v += [ring[0][0], ring[0][1], h, ring[k][0], ring[k][1], h, ring[k + 1][0], ring[k + 1][1], h]
        n += 1

    # per-axis 16-bit quantization
    mn = [min(v[i::3]) for i in range(3)]
    mx = [max(v[i::3]) for i in range(3)]
    span = [(mx[a] - mn[a]) or 1.0 for a in range(3)]
    qs = array("H", [0]) * len(v)
    for i in range(len(v)):
        a = i % 3
        qs[i] = max(0, min(65535, int(round((v[i] - mn[a]) / span[a] * 65535))))
    if sys.byteorder == "big":
        qs.byteswap()

    _DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(_DIR / "downtown-buildings.bin", "wb", compresslevel=7) as f:
        f.write(qs.tobytes())
    (_DIR / "downtown-buildings.json").write_text(
        json.dumps({"quant": {"min": mn, "max": mx}, "n_vertices": len(v) // 3})
    )
    mb = (_DIR / "downtown-buildings.bin").stat().st_size / 1e6
    print(f"Done. downtown buildings: {n:,} | triangles: {len(v)//9:,} | gz {mb:.1f} MB")


if __name__ == "__main__":
    main()
