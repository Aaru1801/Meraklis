"""City of Toronto **3D Massing** adapter (footprint geometry + building height).

Reads the small local cache produced by ``openhouse.scripts.ingest_massing`` (the
heavy 428k-footprint shapefile is processed once, offline). Keyed by RSN, so the
building must be resolved first. This is an enrichment / visualization +
height-cross-check source — it is never used to change the risk score.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .base import AddressQuery, AdapterResult, SourceAdapter, SourceStatus

DEFAULT_MASSING_CACHE = Path(
    os.environ.get(
        "OPENHOUSE_MASSING_CACHE",
        str(Path(__file__).resolve().parents[4] / "data" / "massing_cache.json"),
    )
)


class MassingAdapter(SourceAdapter):
    """Serves cached 3D-Massing footprint + height for a resolved building."""

    name = "toronto_3d_massing"
    base_confidence = 0.9  # Lidar-derived municipal 3D model

    def __init__(self, cache_path: Path | str | None = None):
        self._cache_path = Path(cache_path or DEFAULT_MASSING_CACHE)
        self._cache: dict | None = None

    def _load(self) -> dict:
        if self._cache is None:
            try:
                self._cache = json.loads(self._cache_path.read_text())
            except Exception:  # noqa: BLE001 - missing/corrupt cache → empty
                self._cache = {"buildings": {}}
        return self._cache

    def available(self) -> bool:
        return self._cache_path.exists()

    def _fetch(self, query: AddressQuery) -> AdapterResult:
        if not query.rsn:
            return AdapterResult(
                self.name,
                SourceStatus.UNAVAILABLE,
                0.0,
                note="3D Massing is keyed by building (RSN); resolve the building first.",
            )
        cache = self._load()
        b = cache.get("buildings", {}).get(query.rsn)
        if not b or not b.get("matched"):
            return AdapterResult(
                self.name,
                SourceStatus.UNAVAILABLE,
                0.0,
                note=(
                    "No 3D Massing footprint cached for this building. Run "
                    "`python -m openhouse.scripts.ingest_massing` to add it."
                ),
            )
        return AdapterResult(
            source=self.name,
            status=SourceStatus.OK,
            confidence=self.base_confidence,
            note=(
                f"{b.get('height_source', 'City')} footprint {b.get('distance_m')} m from "
                f"the registered location; roof ~{b.get('max_height_m')} m."
            ),
            data={
                "massing": b,
                "source": cache.get("source"),
                "source_url": cache.get("source_url"),
            },
        )
