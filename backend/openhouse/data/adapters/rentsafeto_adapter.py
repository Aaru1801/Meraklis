"""RentSafeTO / City of Toronto Open Data adapter (the primary, trusted source)."""

from __future__ import annotations

import datetime as dt

from ...risk import assess
from ..address import match_score, normalize_address
from ..store import BuildingStore
from .base import AddressQuery, AdapterResult, SourceAdapter, SourceStatus


class RentSafeToAdapter(SourceAdapter):
    """Official municipal inspection data — the spine of OpenHouse.

    Resolves a query by RSN (exact) or by fuzzy address match against the local
    store, then attaches the full deterministic risk report. Confidence reflects
    match quality and how recent the inspection is.
    """

    name = "rentsafeto"
    base_confidence = 0.95

    def __init__(self, store: BuildingStore | None = None):
        self._store = store

    @property
    def store(self) -> BuildingStore:
        if self._store is None:
            self._store = BuildingStore()
        return self._store

    def available(self) -> bool:
        try:
            return self.store.count()["buildings"] > 0
        except Exception:  # noqa: BLE001
            return False

    def _resolve(self, query: AddressQuery) -> tuple[str | None, float, str]:
        """Return (rsn, match_confidence, note)."""
        if query.rsn and self.store.get_building(query.rsn) is not None:
            return query.rsn, 1.0, "Matched by RSN."
        if query.raw_address:
            # Search with a normalized term ("1182 queen") so "Street West" still
            # finds stored "ST W"; then rank candidates by full match score.
            na = normalize_address(query.raw_address)
            search_term = f"{na.street_number or ''} {na.street_name}".strip() or query.raw_address
            hits = self.store.search(search_term, 15)
            best_rsn, best_score = None, 0.0
            for h in hits:
                s = match_score(query.raw_address, h.address)
                if s > best_score:
                    best_score, best_rsn = s, h.rsn
            if best_rsn and best_score >= 0.7:
                return best_rsn, best_score, f"Matched by address (score {best_score:.2f})."
            if best_rsn and best_score >= 0.5:
                return best_rsn, best_score, (
                    f"Approximate address match (score {best_score:.2f}) — verify the building."
                )
        return None, 0.0, "No RentSafeTO record matched this query."

    def _fetch(self, query: AddressQuery) -> AdapterResult:
        rsn, match_conf, note = self._resolve(query)
        if rsn is None:
            return AdapterResult(self.name, SourceStatus.UNAVAILABLE, 0.0, note=note)

        building = self.store.get_building(rsn)
        report = assess(building)

        status = SourceStatus.OK if match_conf >= 0.7 else SourceStatus.UNCERTAIN
        confidence = self.base_confidence * match_conf

        # Stale-data downgrade.
        if report.evaluation_date:
            age = (dt.date.today() - report.evaluation_date).days / 365.25
            if age >= 4:
                status = SourceStatus.UNCERTAIN
                confidence = min(confidence, 0.75)
                note += f" Inspection is ~{age:.0f} years old."

        return AdapterResult(
            source=self.name,
            status=status,
            confidence=round(confidence, 2),
            note=note.strip(),
            data={
                "rsn": rsn,
                "report": report.model_dump(mode="json"),
            },
        )
