"""Extract iconic Toronto landmarks as their ORIGINAL detailed 3D models.

For instant "this is Toronto" recognition, a handful of landmarks (CN Tower,
Rogers Centre, Scotiabank Arena, City Hall, …) are rendered from the *detailed*
3D-Massing Multipatch geometry — NOT the flat footprint extrusion. We find each
landmark's building in the .gdb by location, triangulate its real faces, and
emit every vertex as true (lng, lat, height). The MapLibre custom layer converts
those to mercator coordinates in JS, so there's no axis/transform guesswork.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_landmarks \
        --gdb TorontoBuildingModels/_work/3DMassingMultipatch_2025_WGS84.gdb
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import fiona

R = 6378137.0
MATCH_RADIUS_M = 115.0
MAX_TRIS = 45000  # skip giant merged complexes (a single landmark is far smaller)
_OUT = Path(__file__).resolve().parents[3] / "frontend" / "public" / "landmarks.json"

# name, lng, lat (building centres). Only landmarks that exist as a CLEAN single
# feature in the Multipatch are listed. Deliberately excluded:
#   • Scotiabank Arena  — merged with the 238 m Maple Leaf Square condo towers;
#                         no separable arena feature (shows as grey massing).
#   • New City Hall     — a single 361k-triangle merged complex; too heavy to ship
#                         (its curved towers still render as grey massing at ~99 m).
LANDMARKS: list[tuple[str, float, float]] = [
    ("CN Tower", -79.38711, 43.64256),
    ("Rogers Centre", -79.38915, 43.64147),
    ("Old City Hall", -79.38170, 43.65250),
    ("Union Station", -79.38066, 43.64531),
    ("Royal Ontario Museum", -79.39476, 43.66773),
    ("Casa Loma", -79.40942, 43.67803),
]


def merc_to_lnglat(x: float, y: float) -> tuple[float, float]:
    return (
        x / R * 180.0 / math.pi,
        (2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * 180.0 / math.pi,
    )


def lnglat_to_merc(lng: float, lat: float) -> tuple[float, float]:
    x = lng * math.pi / 180.0 * R
    y = math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0)) * R
    return x, y


def _dist_m(lat1, lng1, lat2, lng2) -> float:
    dx = (lng2 - lng1) * math.cos(math.radians(lat1)) * 111320.0
    dy = (lat2 - lat1) * 110540.0
    return math.hypot(dx, dy)


def _triangulate(coords) -> tuple[list[float], int, float, float]:
    """MultiPolygon Z -> flat [lng,lat,h,...] triangles + (#tris, minH, maxH)."""
    out: list[float] = []
    minh, maxh = 1e9, -1e9
    for poly in coords:
        if not poly:
            continue
        ring = poly[0]
        pts = []
        for p in ring:
            lng, lat = merc_to_lnglat(p[0], p[1])
            h = float(p[2]) if len(p) > 2 and p[2] is not None else 0.0
            minh, maxh = min(minh, h), max(maxh, h)
            pts.append((round(lng, 6), round(lat, 6), round(h, 1)))
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        for k in range(1, len(pts) - 1):
            out.extend(pts[0]); out.extend(pts[k]); out.extend(pts[k + 1])
    return out, len(out) // 9, (minh if minh < 1e9 else 0), (maxh if maxh > -1e9 else 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb", default="TorontoBuildingModels/_work/3DMassingMultipatch_2025_WGS84.gdb")
    args = ap.parse_args()

    targets = [{"name": n, "lng": lng, "lat": lat, "best_dist": 1e9, "best": None} for n, lng, lat in LANDMARKS]

    layers = [l for l in fiona.listlayers(args.gdb) if l.startswith("Multipatch_")]
    print(f"scanning {len(layers)} layers for {len(targets)} landmarks…")
    for li, layer in enumerate(layers):
        with fiona.open(args.gdb, layer=layer) as src:
            for feat in src:
                geom = feat.get("geometry")
                coords = geom.get("coordinates") if geom else None
                if not coords:
                    continue
                sx = sy = 0.0; n = 0
                for poly in coords:
                    for p in poly[0]:
                        sx += p[0]; sy += p[1]; n += 1
                if not n:
                    continue
                clng, clat = merc_to_lnglat(sx / n, sy / n)
                for t in targets:
                    d = _dist_m(clat, clng, t["lat"], t["lng"])
                    if d <= MATCH_RADIUS_M and d < t["best_dist"]:
                        t["best_dist"] = d
                        t["best"] = coords
        if (li + 1) % 40 == 0:
            print(f"  …{li + 1}/{len(layers)} layers")

    landmarks = []
    for t in targets:
        if not t["best"]:
            print(f"  ✗ {t['name']}: no massing model within {MATCH_RADIUS_M:.0f} m")
            continue
        tris, ntri, minh, maxh = _triangulate(t["best"])
        if ntri < 1:
            print(f"  ✗ {t['name']}: empty geometry")
            continue
        if ntri > MAX_TRIS:
            print(f"  ✗ {t['name']:22s} {ntri} tris > cap — likely a merged complex, skipped")
            continue
        landmarks.append({"name": t["name"], "anchor": [t["lng"], t["lat"]], "v": tris})
        print(f"  ✓ {t['name']:22s} tris={ntri:5d}  height {minh:.0f}–{maxh:.0f} m")

    _OUT.write_text(json.dumps({"landmarks": landmarks}, separators=(",", ":")))
    kb = _OUT.stat().st_size / 1e3
    print(f"\nDone. {len(landmarks)} landmark models → {_OUT} ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
