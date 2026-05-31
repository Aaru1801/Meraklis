"""Ingest Statistics Canada Open Database of Buildings (ODB) geometry for buildings into a small cache.

This script replaces the old ingest_massing.py. It uses the accurate ODB Geopackages
to spatially match a building's RentSafeTO registered location to its nearest
footprint, then writes a tiny JSON cache (footprint ring + heights)
that the app reads at runtime.

Usage:
    PYTHONPATH=backend python -m openhouse.scripts.ingest_odb
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sqlite3
from pathlib import Path

from shapely import from_wkb
from shapely.ops import transform
from pyproj import Transformer
from openhouse.agents.edge import DEMO_ADDRESSES
from openhouse.data.store import DEFAULT_DB_PATH, BuildingStore

DEFAULT_CACHE = Path(__file__).resolve().parents[3] / "data" / "massing_cache.json"

# Match prefilter: only consider footprints within 250m box
_PAD = 250.0

to_3347 = Transformer.from_crs("EPSG:4326", "EPSG:3347", always_xy=True)
to_4326 = Transformer.from_crs("EPSG:3347", "EPSG:4326", always_xy=True)

def _largest_ring(shape) -> list[tuple[float, float]]:
    """Return the exterior (largest) ring of a polygon in WGS84."""
    if shape.geom_type == 'Polygon':
        return list(shape.exterior.coords)
    elif shape.geom_type == 'MultiPolygon':
        largest = max(shape.geoms, key=lambda p: p.area)
        return list(largest.exterior.coords)
    else:
        # Fallback
        return list(shape.coords)

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
        t_x, t_y = to_3347.transform(b.longitude, b.latitude)
        out[rsn] = {
            "address": b.address,
            "lat": b.latitude,
            "lon": b.longitude,
            "t_x": t_x,
            "t_y": t_y,
            "storeys": b.storeys,
        }
    return out

def _extract_wkb(geom_blob: bytes) -> bytes:
    """Extract standard WKB from GeoPackage Geometry blob with variable length header."""
    flags = geom_blob[3]
    env_ind = (flags & 0x0E) >> 1
    if env_ind == 0:
        hdr_len = 8
    elif env_ind == 1:
        hdr_len = 40
    elif env_ind in (2, 3):
        hdr_len = 56
    elif env_ind == 4:
        hdr_len = 72
    else:
        hdr_len = 8
    return geom_blob[hdr_len:]

def ingest(odb_paths: list[str], targets: dict[str, dict]) -> dict:
    best = {rsn: {"d": 1e18, "rec": None} for rsn in targets}

    for db_path in odb_paths:
        print(f"Scanning {db_path}...")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            table_name = Path(db_path).stem
            # Query only Toronto buildings to speed up
            cur.execute(f"SELECT geom, height, floors, sq_ft FROM {table_name} WHERE csdname = 'Toronto';")
            
            for row in cur:
                geom_blob, height, floors, sq_ft = row
                
                wkb = _extract_wkb(geom_blob)
                try:
                    shape = from_wkb(wkb)
                except Exception:
                    continue
                
                la, lo = shape.centroid.y, shape.centroid.x
                
                for rsn, t in targets.items():
                    if abs(lo - t["t_x"]) > _PAD or abs(la - t["t_y"]) > _PAD:
                        continue
                    d = math.hypot(lo - t["t_x"], la - t["t_y"])
                    if d < best[rsn]["d"]:
                        best[rsn] = {
                            "d": d, 
                            "rec": row, 
                            "shape": shape,
                            "c_lat": la,
                            "c_lon": lo
                        }
            conn.close()
        except Exception as e:
            print(f"  ! Error reading {db_path}: {e}")

    buildings: dict[str, dict] = {}
    for rsn, t in targets.items():
        sel = best[rsn]
        if sel["d"] > 250: # Arbitrary max match distance
            print(f"  ! {rsn} {t['address']}: no footprint within ~250 m")
            buildings[rsn] = {"matched": False, "address": t["address"]}
            continue
            
        geom_blob, height, floors, sq_ft = sel["rec"]
        shape = sel["shape"]
        c_lat, c_lon = sel["c_lat"], sel["c_lon"] # In EPSG:3347
        
        # ring_native is in EPSG:3347
        ring_native = _largest_ring(shape)
        
        # ring_lonlat is in WGS84
        ring_lonlat = [to_4326.transform(x, y) for x, y in ring_native]
        
        # Centroid in WGS84
        wgs_lon, wgs_lat = to_4326.transform(c_lon, c_lat)
        
        # Calculate local ground metres relative to centroid
        ring_m = [((x - c_lon), (y - c_lat)) for x, y in ring_native]
        area = _shoelace_area_m2(ring_m)
        
        h_val = float(height) if height and height != '..' else (float(t["storeys"] or 0) * 3.0)
        
        buildings[rsn] = {
            "matched": True,
            "address": t["address"],
            "rentsafeto_storeys": t["storeys"],
            "distance_m": round(sel["d"], 1),
            "min_height_m": round(h_val, 1),
            "avg_height_m": round(h_val, 1),
            "max_height_m": round(h_val, 1),
            "surface_elev_m": 0.0,
            "height_source": "ODB (Statistics Canada)" if height and height != '..' else "Estimated from storeys",
            "footprint_area_m2": round(area, 1),
            "centroid": {"lat": round(wgs_lat, 6), "lon": round(wgs_lon, 6)},
            "footprint_lonlat": [[round(x, 6), round(y, 6)] for x, y in ring_lonlat],
            "footprint_m": [[round(x, 2), round(y, 2)] for x, y in ring_m],
            "n_vertices": len(ring_m),
            "massing_year": 2026,
        }
        print(
            f"  [OK] {rsn} {t['address']}: footprint {sel['d']:.1f} m away · "
            f"height {h_val:.1f} m · {area:.0f} m² · "
            f"{len(ring_m)} verts"
        )

    return {
        "source": "Statistics Canada — Open Database of Buildings (ODB v3)",
        "source_url": "https://www.statcan.gc.ca/en/lode/databases/odb",
        "note": (
            "Footprint + building height matched to each building's RentSafeTO "
            "registered location by nearest ODB footprint. Enrichment / "
            "visualization + height cross-check only."
        ),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "buildings": buildings,
    }

def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest accurate ODB footprints for buildings.")
    ap.add_argument("--rsn", action="append", help="RSN to cache (repeatable). Default: demo buildings.")
    ap.add_argument("--out", default=str(DEFAULT_CACHE), help="Output cache JSON path.")
    ap.add_argument("--odb-dir", default=str(Path(DEFAULT_DB_PATH).parent), help="Directory containing ODB_v3_ON_* folders.")
    args = ap.parse_args()

    odb_paths = [
        str(Path(args.odb_dir) / f"ODB_v3_ON_{i}" / f"ODB_v3_ON_{i}.gpkg")
        for i in range(1, 4)
    ]
    
    store = BuildingStore()
    targets = _targets(args.rsn, store)
    if not targets:
        raise SystemExit("No resolvable target buildings.")
        
    print(f"Matching {len(targets)} building(s) against ODB ...")
    cache = ingest(odb_paths, targets)
    store.close()

    Path(args.out).write_text(json.dumps(cache, indent=2))
    n = sum(1 for b in cache["buildings"].values() if b.get("matched"))
    print(f"\n[OK] Wrote {n}/{len(targets)} matched building(s) -> {args.out}")

if __name__ == "__main__":
    main()
