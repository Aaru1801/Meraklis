"""Ingest the live RentSafeTO dataset into the local SQLite store.

Usage:
    python -m openhouse.scripts.ingest                # full dataset
    python -m openhouse.scripts.ingest --limit 500    # quick sample
    python -m openhouse.scripts.ingest --current-only # skip pre-2023 history
"""

from __future__ import annotations

import argparse
import logging
import time

from openhouse.data.rentsafeto import fetch_all_evaluations
from openhouse.data.store import DEFAULT_DB_PATH, BuildingStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest RentSafeTO data into SQLite.")
    parser.add_argument("--limit", type=int, default=None, help="Cap records per resource.")
    parser.add_argument("--current-only", action="store_true", help="Skip pre-2023 resource.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite path.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("ingest")

    t0 = time.time()
    log.info("Fetching RentSafeTO evaluations from open.toronto.ca …")
    evals = fetch_all_evaluations(
        include_pre2023=not args.current_only, limit_per_resource=args.limit
    )
    log.info("Fetched %d evaluations in %.1fs", len(evals), time.time() - t0)

    store = BuildingStore(args.db)
    stats = store.ingest(evals)
    city = store.city_stats()
    store.close()

    log.info("Ingest complete: %s", stats)
    log.info("City snapshot: %s", city)
    print(
        f"\n✅ Ingested {stats['buildings']:,} buildings "
        f"({stats['evaluations']:,} evaluations) → {args.db}\n"
        f"   City-wide average score: {city.get('avg_score')}  |  "
        f"high-risk (<65): {city.get('n_high_risk')}"
    )


if __name__ == "__main__":
    main()
