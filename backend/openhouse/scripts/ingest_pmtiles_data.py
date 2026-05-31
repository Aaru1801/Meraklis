"""Emit line-delimited GeoJSON of ALL Toronto building footprints for tippecanoe.

Feeds the self-hosted offline vector tiles (toronto.pmtiles): every building in
the City 3D-Massing shapefile (~428k) as a footprint polygon (WGS84 lng/lat) with
its height, so the MapLibre map can extrude the whole city in 3D — even buildings
with no RentSafeTO listing (navigation context). Iconic landmarks are tagged so
their generic footprint slab can be hidden and replaced with detailed multipatch
meshes in the browser.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_pmtiles_data \
        --shp TorontoBuildingModels/_fp/3DMassingShapefile_2025_WGS84.shp \
        --out TorontoBuildingModels/_tiles/buildings.ndjson
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import shapefile  # pyshp

from .ingest_landmarks import LANDMARKS

R = 6378137.0
LANDMARK_MASK_RADIUS_M = {
    "CN Tower": 38.0,
    "Rogers Centre": 78.0,
    "Old City Hall": 56.0,
    "Union Station": 52.0,
    "Royal Ontario Museum": 52.0,
    "Casa Loma": 70.0,
}


def merc_to_lnglat(x: float, y: float) -> tuple[float, float]:
    return (
        round(x / R * 180.0 / math.pi, 6),
        round((2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * 180.0 / math.pi, 6),
    )


def _dist_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dx = (lng2 - lng1) * math.cos(math.radians(lat1)) * 111320.0
    dy = (lat2 - lat1) * 110540.0
    return math.hypot(dx, dy)


def landmark_for(lng: float, lat: float) -> str | None:
    for name, target_lng, target_lat in LANDMARKS:
        radius = LANDMARK_MASK_RADIUS_M.get(name, 0.0)
        if radius and _dist_m(lat, lng, target_lat, target_lng) <= radius:
            return name
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp", default="TorontoBuildingModels/_fp/3DMassingShapefile_2025_WGS84.shp")
    ap.add_argument("--out", default="TorontoBuildingModels/_tiles/buildings.ndjson")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    sf = shapefile.Reader(args.shp)
    fi = {name: k for k, name in enumerate([f[0] for f in sf.fields[1:]])}
    n = 0
    with out.open("w") as f:
        for sr in sf.iterShapeRecords():
            shp = sr.shape
            if not shp.points:
                continue
            rec = sr.record
            h = rec[fi["MAX_HEIGHT"]] or rec[fi["AVG_HEIGHT"]] or 0.0
            h = round(float(h or 0.0), 1) or 6.0
            lng, lat = rec[fi["LONGITUDE"]], rec[fi["LATITUDE"]]
            landmark = landmark_for(float(lng), float(lat)) if lng is not None and lat is not None else None
            parts = list(shp.parts) + [len(shp.points)]
            ring = shp.points[parts[0]:parts[1]]  # exterior ring
            coords = [list(merc_to_lnglat(x, y)) for (x, y) in ring]
            if len(coords) < 4:
                continue
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            props: dict[str, object] = {"h": h}
            if landmark:
                props.update({"lm": 1, "name": landmark})
            f.write(json.dumps({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coords]},
                "properties": props,
            }, separators=(",", ":")))
            f.write("\n")
            n += 1
            if n % 100_000 == 0:
                print(f"  {n:,} buildings written…")

    mb = out.stat().st_size / 1e6
    print(f"Done. {n:,} building features → {out} ({mb:.0f} MB)")


if __name__ == "__main__":
    main()
