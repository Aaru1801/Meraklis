"""Ingest City of Toronto **3D Massing** geometry for buildings into a small cache.

The official dataset is ~428k building footprints distributed as a large zipped
shapefile (no query API). This script does the heavy lifting **once, offline**:
it spatially matches a building's RentSafeTO registered location to its nearest
3D-Massing footprint, then writes a tiny JSON cache (footprint ring + heights)
that the app reads at runtime — so the runtime stays dependency-free and offline.

This is an *enrichment / visualization + cross-check* source. It is NEVER used to
change the deterministic risk score.

Setup (one-time):
    1. Download a "3DMassingShapefile_<year>_WGS84.zip" from
       https://open.toronto.ca/dataset/3d-massing/  and unzip it.
    2. pip install pyshp     # pure-Python shapefile reader (ingest-only dep)

Usage:
    PYTHONPATH=backend python -m openhouse.scripts.ingest_massing \
        --shapefile data/_massing_src/3DMassingShapefile_2025_WGS84 [--year 2025]
    # default: caches the demo buildings; add --rsn <RSN> (repeatable) for more.

Notes on the data:
    • Fields: MIN/MAX/AVG_HEIGHT (metres above grade), HEIGHT_MSL, SURF_ELEV,
      HEIGHT_SRC (e.g. "Lidar-Derived"), LATITUDE/LONGITUDE (WGS84 representative
      point per footprint).
    • Geometry coordinates are Web Mercator (EPSG:3857) metres — converted here
      to WGS84 lon/lat and to local ground-metres for rendering.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

from openhouse.agents.edge import DEMO_ADDRESSES
from openhouse.data.store import DEFAULT_DB_PATH, BuildingStore

_R = 6378137.0  # Web Mercator sphere radius (EPSG:3857)
DEFAULT_CACHE = Path(__file__).resolve().parents[3] / "data" / "massing_cache.json"
SOURCE_URL = "https://open.toronto.ca/dataset/3d-massing/"

# Match prefilter: only consider footprints within this lat/long box of the point
# (~250 m), then choose the nearest by haversine.
_LAT_PAD = 0.0025
_LON_PAD = 0.0035


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    a = (
        math.sin((lat2 - lat1) * p / 2) ** 2
        + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    )
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def _merc_to_lonlat(x: float, y: float) -> tuple[float, float]:
    lon = math.degrees(x / _R)
    lat = math.degrees(2 * math.atan(math.exp(y / _R)) - math.pi / 2)
    return lon, lat


def _largest_ring(shape) -> list[tuple[float, float]]:
    """Return the exterior (largest) ring of a (multi-part) polygon, in Web Mercator."""
    pts = [(float(px), float(py)) for px, py in shape.points]
    parts = list(shape.parts) + [len(pts)]
    rings = [pts[parts[i]: parts[i + 1]] for i in range(len(parts) - 1)]
    if not rings:
        return pts
    return max(rings, key=len)


def _shoelace_area_m2(ring_m: list[tuple[float, float]]) -> float:
    a = 0.0
    n = len(ring_m)
    for i in range(n):
        x1, y1 = ring_m[i]
        x2, y2 = ring_m[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _targets(rsns: list[str] | None, store: BuildingStore) -> dict[str, dict]:
    """Resolve target RSNs → {rsn: {address, lat, lon, storeys}}."""
    rsn_list = rsns or [d["rsn"] for d in DEMO_ADDRESSES]
    out: dict[str, dict] = {}
    for rsn in rsn_list:
        b = store.get_building(rsn)
        if not b or b.latitude is None or b.longitude is None:
            print(f"  ! skipping {rsn}: not in store or missing coordinates")
            continue
        out[rsn] = {
            "address": b.address,
            "lat": b.latitude,
            "lon": b.longitude,
            "storeys": b.storeys,
        }
    return out


def ingest(shapefile_base: str, targets: dict[str, dict], year: int) -> dict:
    import shapefile  # local import: ingest-only dependency

    reader = shapefile.Reader(shapefile_base)
    fields = [f[0] for f in reader.fields[1:]]
    iLat, iLon = fields.index("LATITUDE"), fields.index("LONGITUDE")
    iMin, iAvg, iMax = (
        fields.index("MIN_HEIGHT"),
        fields.index("AVG_HEIGHT"),
        fields.index("MAX_HEIGHT"),
    )
    iSrc, iElev = fields.index("HEIGHT_SRC"), fields.index("SURF_ELEV")

    # One streaming pass over the DBF (cheap — no geometry) to find the nearest
    # footprint record index for each target point.
    best = {rsn: {"d": 1e18, "idx": -1, "rec": None} for rsn in targets}
    for idx, rec in enumerate(reader.iterRecords()):
        la, lo = rec[iLat], rec[iLon]
        if la is None or lo is None:
            continue
        for rsn, t in targets.items():
            if abs(la - t["lat"]) > _LAT_PAD or abs(lo - t["lon"]) > _LON_PAD:
                continue
            d = _haversine_m(t["lat"], t["lon"], la, lo)
            if d < best[rsn]["d"]:
                best[rsn] = {"d": d, "idx": idx, "rec": rec}

    buildings: dict[str, dict] = {}
    for rsn, t in targets.items():
        sel = best[rsn]
        if sel["idx"] < 0:
            print(f"  ! {rsn} {t['address']}: no footprint within ~250 m")
            buildings[rsn] = {"matched": False, "address": t["address"]}
            continue
        rec = sel["rec"]
        shape = reader.shape(sel["idx"])  # random access via .shx — only 1 read
        ring_merc = _largest_ring(shape)
        # centroid in Web Mercator
        cx = sum(p[0] for p in ring_merc) / len(ring_merc)
        cy = sum(p[1] for p in ring_merc) / len(ring_merc)
        c_lon, c_lat = _merc_to_lonlat(cx, cy)
        scale = math.cos(math.radians(c_lat))  # Mercator → true ground metres
        ring_lonlat = [list(_merc_to_lonlat(x, y)) for x, y in ring_merc]
        ring_m = [((x - cx) * scale, (y - cy) * scale) for x, y in ring_merc]
        area = _shoelace_area_m2(ring_m)
        max_h = float(rec[iMax] or 0.0)
        avg_h = float(rec[iAvg] or 0.0)
        buildings[rsn] = {
            "matched": True,
            "address": t["address"],
            "rentsafeto_storeys": t["storeys"],
            "distance_m": round(sel["d"], 1),
            "min_height_m": round(float(rec[iMin] or 0.0), 1),
            "avg_height_m": round(avg_h, 1),
            "max_height_m": round(max_h, 1),
            "surface_elev_m": round(float(rec[iElev] or 0.0), 1),
            "height_source": str(rec[iSrc] or "").strip() or "unspecified",
            "footprint_area_m2": round(area, 1),
            "centroid": {"lat": round(c_lat, 6), "lon": round(c_lon, 6)},
            "footprint_lonlat": [[round(x, 6), round(y, 6)] for x, y in ring_lonlat],
            "footprint_m": [[round(x, 2), round(y, 2)] for x, y in ring_m],
            "n_vertices": len(ring_m),
            "massing_year": year,
        }
        print(
            f"  ✓ {rsn} {t['address']}: footprint {sel['d']:.1f} m away · "
            f"avg {avg_h:.1f} m / max {max_h:.1f} m · {area:.0f} m² · "
            f"{len(ring_m)} verts · {buildings[rsn]['height_source']}"
        )
    reader.close()

    return {
        "source": f"City of Toronto Open Data — 3D Massing ({year}, WGS84)",
        "source_url": SOURCE_URL,
        "note": (
            "Footprint + building height matched to each building's RentSafeTO "
            "registered location by nearest 3D-Massing footprint. Enrichment / "
            "visualization + height cross-check only — never used in risk scoring."
        ),
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "buildings": buildings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest 3D Massing footprints for buildings.")
    ap.add_argument(
        "--shapefile",
        default=str(Path(DEFAULT_DB_PATH).parent / "_massing_src" / "3DMassingShapefile_2025_WGS84"),
        help="Shapefile base path (no extension).",
    )
    ap.add_argument("--year", type=int, default=2025, help="Massing dataset year (for provenance).")
    ap.add_argument("--rsn", action="append", help="RSN to cache (repeatable). Default: demo buildings.")
    ap.add_argument("--out", default=str(DEFAULT_CACHE), help="Output cache JSON path.")
    args = ap.parse_args()

    store = BuildingStore()
    targets = _targets(args.rsn, store)
    if not targets:
        raise SystemExit("No resolvable target buildings.")
    print(f"Matching {len(targets)} building(s) against {args.shapefile} …")
    cache = ingest(args.shapefile, targets, args.year)
    store.close()

    Path(args.out).write_text(json.dumps(cache, indent=2))
    n = sum(1 for b in cache["buildings"].values() if b.get("matched"))
    print(f"\n✅ Wrote {n}/{len(targets)} matched building(s) → {args.out}")


if __name__ == "__main__":
    main()
