"""Ingest the operator (property-management company) field for each building.

RentSafeTO *evaluations* (our main dataset) carry no operator/landlord field, so
the deterministic core can't link a building to the company that runs it. The
City's separate **Apartment Building Registration** open dataset does carry it
(`PROP_MANAGEMENT_COMPANY_NAME`), keyed by the same RSN. This one-time pull joins
that field into a small ``building_operators(rsn, operator_raw)`` table so the
Operator/Portfolio agent can resolve an operator and analyse its whole portfolio.

It writes a SEPARATE table (not a column on ``buildings``) so re-running the main
evaluation ingest never clobbers it. The committed SQLite already includes the
table; re-run only to refresh from the live City API.

    PYTHONPATH=backend python -m openhouse.scripts.ingest_operators
"""

from __future__ import annotations

import sqlite3

import httpx

from ..data.store import DEFAULT_DB_PATH

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
REGISTRATION_SLUG = "apartment-building-registration"
PAGE_SIZE = 10_000


def _resolve_resource_id(client: httpx.Client) -> str:
    r = client.get(f"{CKAN_BASE}/package_show", params={"id": REGISTRATION_SLUG})
    r.raise_for_status()
    pkg = r.json()["result"]
    live = [res for res in pkg["resources"] if res.get("datastore_active")]
    if not live:
        raise RuntimeError(f"No datastore_active resource in '{REGISTRATION_SLUG}'.")
    return live[0]["id"]


def _fetch_all(client: httpx.Client, resource_id: str) -> list[dict]:
    rows: list[dict] = []
    offset, total = 0, None
    while total is None or offset < total:
        r = client.get(
            f"{CKAN_BASE}/datastore_search",
            params={"resource_id": resource_id, "limit": PAGE_SIZE, "offset": offset},
        )
        r.raise_for_status()
        result = r.json()["result"]
        total = result["total"]
        recs = result["records"]
        if not recs:
            break
        rows.extend(recs)
        offset += len(recs)
        print(f"  registration: {len(rows):,} / {total:,}")
    return rows


def main() -> None:
    print(f"Fetching '{REGISTRATION_SLUG}' from CKAN…")
    with httpx.Client(timeout=60.0) as client:
        resource_id = _resolve_resource_id(client)
        rows = _fetch_all(client, resource_id)

    # rsn -> operator_raw (trimmed, non-empty only)
    operators: dict[str, str] = {}
    for r in rows:
        rsn = str(r.get("RSN") or "").strip()
        name = str(r.get("PROP_MANAGEMENT_COMPANY_NAME") or "").strip()
        if rsn and name:
            operators[rsn] = name

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS building_operators (
            rsn TEXT PRIMARY KEY,
            operator_raw TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_op_raw ON building_operators(operator_raw)")
    conn.execute("DELETE FROM building_operators")
    conn.executemany(
        "INSERT OR REPLACE INTO building_operators (rsn, operator_raw) VALUES (?, ?)",
        list(operators.items()),
    )
    conn.commit()

    # Density report — how many of our buildings now have an operator on file.
    n_buildings = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
    n_matched = conn.execute(
        "SELECT COUNT(*) FROM buildings b "
        "JOIN building_operators o ON o.rsn = b.rsn"
    ).fetchone()[0]
    n_distinct = conn.execute(
        "SELECT COUNT(DISTINCT operator_raw) FROM building_operators"
    ).fetchone()[0]
    conn.close()

    pct = round(100 * n_matched / n_buildings, 1) if n_buildings else 0.0
    print("\nDone. Operator coverage:")
    print(f"  registration rows with operator : {len(operators):,}")
    print(f"  our buildings matched           : {n_matched:,} / {n_buildings:,} ({pct}%)")
    print(f"  distinct operator spellings     : {n_distinct:,}")
    if pct < 40:
        print("  ⚠ density gate: <40% — portfolio analysis will be thin.")


if __name__ == "__main__":
    main()
