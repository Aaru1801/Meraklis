"""Client for the City of Toronto RentSafeTO open-data API (CKAN datastore).

No API key is required. The datastore exposes paginated records via
``datastore_search``; we page through in blocks and normalize into typed
:class:`~openhouse.data.models.Evaluation` objects.

Dataset: "Apartment Building Evaluation"
https://open.toronto.ca/dataset/apartment-building-evaluation/
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .models import Evaluation

log = logging.getLogger("openhouse.rentsafeto")

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
DATASTORE_SEARCH = f"{CKAN_BASE}/datastore_search"

# Active datastore resources (datastore_active = true on the dataset).
RESOURCE_CURRENT = "244f7a02-da5c-425b-b55f-fbdd133dd732"   # 2023 → current, granular
RESOURCE_PRE2023 = "b987be09-0c62-4d7d-928c-4a1ecaeaf3f3"   # pre-2023, coarse

PAGE_SIZE = 1000
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


# ---------------------------------------------------------------------------
# Low-level paging
# ---------------------------------------------------------------------------
def _fetch_page(
    client: httpx.Client, resource_id: str, offset: int, limit: int, q: str | None = None
) -> dict[str, Any]:
    params: dict[str, Any] = {"resource_id": resource_id, "limit": limit, "offset": offset}
    if q:
        params["q"] = q
    resp = client.get(DATASTORE_SEARCH, params=params)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(f"CKAN request failed for {resource_id}: {payload!r}")
    return payload["result"]


def fetch_raw_records(resource_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Page through one CKAN resource and return all raw records.

    Args:
        resource_id: CKAN datastore resource id.
        limit: Optional cap on total records (useful for quick tests).
    """
    records: list[dict[str, Any]] = []
    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": "OpenHouse/1.0"}) as client:
        offset = 0
        total: int | None = None
        while True:
            page_limit = PAGE_SIZE
            if limit is not None:
                page_limit = min(PAGE_SIZE, limit - len(records))
                if page_limit <= 0:
                    break
            result = _fetch_page(client, resource_id, offset, page_limit)
            batch = result.get("records", [])
            if total is None:
                total = result.get("total")
            records.extend(batch)
            log.info("fetched %d/%s from %s", len(records), total, resource_id[:8])
            if not batch or (total is not None and len(records) >= total):
                break
            offset += len(batch)
    return records


def fetch_evaluations(resource_id: str, limit: int | None = None) -> list[Evaluation]:
    """Fetch and parse evaluations from one resource."""
    raw = fetch_raw_records(resource_id, limit=limit)
    out: list[Evaluation] = []
    for rec in raw:
        try:
            ev = Evaluation.from_ckan(rec)
            if ev.rsn:
                out.append(ev)
        except Exception as exc:  # noqa: BLE001 - tolerate occasional bad rows
            log.warning("skipping unparseable record: %s", exc)
    return out


def fetch_all_evaluations(
    include_pre2023: bool = True, limit_per_resource: int | None = None
) -> list[Evaluation]:
    """Fetch evaluations from the current resource (and optionally pre-2023)."""
    evals = fetch_evaluations(RESOURCE_CURRENT, limit=limit_per_resource)
    log.info("current-resource evaluations: %d", len(evals))
    if include_pre2023:
        pre = fetch_evaluations(RESOURCE_PRE2023, limit=limit_per_resource)
        log.info("pre-2023 evaluations: %d", len(pre))
        evals.extend(pre)
    return evals
