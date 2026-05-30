"""Market-listing adapters: Realtor.ca and HouseSigma.

Neither site offers a public API, and both prohibit scraping in their terms of
service. OpenHouse therefore does **not** scrape them live. Instead these
adapters are *pluggable*: if a cached export for a building is dropped into
``data/cache/<source>/<address-key>.json`` (e.g. exported by a licensed feed, a
partner, or the user), it's loaded and surfaced with appropriate (lower)
confidence. Otherwise the adapter degrades gracefully to ``UNAVAILABLE`` with an
honest note.

This keeps the architecture multi-source and future-proof while remaining
compliant and never hallucinating listing data.

Cached file shape (all fields optional):
    {"listed": true, "status": "for_rent", "list_price": 2200,
     "bedrooms": 2, "bathrooms": 1, "sqft": 750, "url": "...", "as_of": "2026-05"}
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import AddressQuery, AdapterResult, SourceAdapter, SourceStatus

DEFAULT_CACHE_ROOT = Path(__file__).resolve().parents[4] / "data" / "cache"


class CachedListingAdapter(SourceAdapter):
    """Base for listing sources backed by an optional local cache export."""

    cache_subdir = "listings"
    base_confidence = 0.5  # cached/third-party market data is inherently softer

    def __init__(self, cache_root: Path | None = None):
        self.cache_dir = (cache_root or DEFAULT_CACHE_ROOT) / self.cache_subdir

    def available(self) -> bool:
        # "Available" if the cache directory exists with any exports.
        return self.cache_dir.exists() and any(self.cache_dir.glob("*.json"))

    def _cache_path(self, query: AddressQuery) -> Path | None:
        key = (query.canonical_address or query.raw_address or query.rsn or "").lower()
        if not key:
            return None
        safe = key.replace(" ", "_").replace("/", "-")
        return self.cache_dir / f"{safe}.json"

    def _fetch(self, query: AddressQuery) -> AdapterResult:
        path = self._cache_path(query)
        if path is None or not path.exists():
            return AdapterResult(
                source=self.name,
                status=SourceStatus.UNAVAILABLE,
                confidence=0.0,
                note=(
                    f"No public API for {self.name}; live scraping is not performed "
                    "(terms of service). Drop a cached export into "
                    f"{self.cache_dir.relative_to(DEFAULT_CACHE_ROOT.parents[1])}/ to enable."
                ),
            )
        data = json.loads(path.read_text())
        # Confidence reflects how fresh the export claims to be.
        confidence = self.base_confidence
        note = "Loaded from cached market export."
        if not data.get("as_of"):
            confidence *= 0.8
            note += " No 'as_of' date — treat as approximate."
        return AdapterResult(
            source=self.name,
            status=SourceStatus.UNCERTAIN,  # third-party market data is never authoritative
            confidence=round(confidence, 2),
            note=note,
            data={"market": data},
        )


class RealtorCaAdapter(CachedListingAdapter):
    """Realtor.ca — cache-only. No public API and scraping is against ToS, so this
    source is 'unavailable' unless a licensed export is dropped into the cache.
    The rent figure OpenHouse shows is a modeled estimate derived from the
    building's RentSafeTO record (see openhouse.data.pio), not from Realtor.ca."""

    name = "realtor.ca"
    cache_subdir = "realtor"


class HouseSigmaAdapter(CachedListingAdapter):
    """HouseSigma — cache-only; 'unavailable' unless a licensed export exists."""

    name = "housesigma"
    cache_subdir = "housesigma"
