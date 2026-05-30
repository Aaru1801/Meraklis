"""Shared data service: search, reports, neighbourhood context, rights.

This is the single source of truth consumed by both the MCP tool server (so the
Research agent can call these as tools) and the orchestrator's direct-context
path. It is pure and LLM-free — it composes the data store, the risk engine and
the knowledge base into the higher-level operations the product needs.
"""

from __future__ import annotations

from functools import lru_cache

from ..data.models import BuildingSummary
from ..data.rent import estimate_rent
from ..data.store import BuildingStore
from ..knowledge import tenant_rights
from ..risk import RiskReport, assess, grade_for, value_band_for, value_index_for


def _risk_band_for_score(score: int | None) -> str:
    """Coarse risk band from the City score alone (for list/map views)."""
    if score is None:
        return "Unknown"
    if score >= 85:
        return "Low"
    if score >= 75:
        return "Moderate"
    if score >= 65:
        return "Elevated"
    if score >= 50:
        return "High"
    return "Severe"


@lru_cache(maxsize=1)
def _store() -> BuildingStore:
    return BuildingStore()


class HousingService:
    """High-level operations over the RentSafeTO dataset."""

    def __init__(self, store: BuildingStore | None = None):
        self.store = store or _store()

    # -- summaries ------------------------------------------------------
    @staticmethod
    def _enrich(summary: BuildingSummary) -> BuildingSummary:
        summary.grade = grade_for(summary.score)
        summary.risk_level = _risk_band_for_score(summary.score)
        est = estimate_rent(
            summary.latitude, summary.longitude, summary.year_built, summary.units, summary.storeys
        )
        summary.estimated_rent = est.monthly if est else None
        summary.value_index = value_index_for(summary.score)
        summary.value_band = value_band_for(summary.score)
        return summary

    @staticmethod
    def _budget_sort(
        rows: list[BuildingSummary], max_rent: int | None, sort: str | None
    ) -> list[BuildingSummary]:
        """Filter by budget and sort by money/score (applied after enrichment)."""
        if max_rent is not None:
            rows = [r for r in rows if r.estimated_rent is not None and r.estimated_rent <= max_rent]
        if sort == "rent_asc":
            rows = sorted(rows, key=lambda r: (r.estimated_rent is None, r.estimated_rent or 0))
        elif sort == "rent_desc":
            rows = sorted(rows, key=lambda r: (r.estimated_rent or 0), reverse=True)
        elif sort == "score_desc":
            rows = sorted(rows, key=lambda r: (r.score or 0), reverse=True)
        elif sort == "score_asc":
            rows = sorted(rows, key=lambda r: (r.score is None, r.score or 0))
        elif sort == "value_desc":
            rows = sorted(rows, key=lambda r: (r.value_index or 0), reverse=True)
        return rows

    def search(
        self,
        query: str,
        limit: int = 25,
        max_rent: int | None = None,
        sort: str | None = None,
    ) -> list[BuildingSummary]:
        rows = [self._enrich(s) for s in self.store.search(query, limit)]
        return self._budget_sort(rows, max_rent, sort)

    def map_points(
        self,
        limit: int = 5000,
        max_score: int | None = None,
        min_score: int | None = None,
        ward_name: str | None = None,
        max_rent: int | None = None,
        sort: str | None = None,
    ) -> list[BuildingSummary]:
        # Pull the full candidate set so budget filtering / rent sorting see every
        # building, then sort and truncate to `limit` (avoids score-order sampling bias).
        rows = [
            self._enrich(s)
            for s in self.store.map_points(
                20000, max_score=max_score, min_score=min_score, ward_name=ward_name
            )
        ]
        return self._budget_sort(rows, max_rent, sort)[:limit]

    def worst(self, limit: int = 10, ward_name: str | None = None) -> list[BuildingSummary]:
        return [self._enrich(s) for s in self.store.worst(limit, ward_name)]

    # -- reports --------------------------------------------------------
    def report(self, rsn: str) -> RiskReport | None:
        building = self.store.get_building(rsn)
        if building is None:
            return None
        return assess(building)

    # -- neighbourhood context -----------------------------------------
    def neighbourhood(self, ward_name: str) -> dict[str, object]:
        stats = self.store.neighbourhood_stats(ward_name)
        worst = self.worst(5, ward_name=ward_name)
        stats["worst_in_ward"] = [
            {"rsn": b.rsn, "address": b.address, "score": b.score, "grade": b.grade}
            for b in worst
        ]
        return stats

    def comparison(self, rsn: str) -> dict[str, object]:
        """How a building ranks within its own ward."""
        report = self.report(rsn)
        if report is None or not report.ward_name or report.overall_score is None:
            return {}
        stats = self.store.neighbourhood_stats(report.ward_name)
        # Percentile: share of ward buildings this one scores at-or-above.
        peers = self.store.map_points(limit=5000, ward_name=report.ward_name)
        scored = [p.score for p in peers if p.score is not None]
        if scored:
            at_or_below = sum(1 for s in scored if s <= report.overall_score)
            percentile = round(100 * at_or_below / len(scored))
        else:
            percentile = None
        return {
            "ward_name": report.ward_name,
            "building_score": report.overall_score,
            "ward_avg_score": stats.get("avg_score"),
            "ward_min_score": stats.get("min_score"),
            "ward_n_buildings": stats.get("n_buildings"),
            "percentile_in_ward": percentile,  # higher = better than more peers
            "vs_ward_avg": (
                round(report.overall_score - stats["avg_score"], 1)
                if stats.get("avg_score") is not None
                else None
            ),
        }

    # -- rights ---------------------------------------------------------
    def rights(self, rsn: str) -> dict[str, object]:
        report = self.report(rsn)
        if report is None:
            return {}
        rights = tenant_rights.relevant_rights(report)
        return {
            "topics": tenant_rights.topics_for(report),
            "rights": [
                {
                    "title": r.title,
                    "right": r.right,
                    "legal_basis": r.legal_basis,
                    "what_you_can_do": list(r.what_you_can_do),
                    "escalation": r.escalation,
                    "source": r.source,
                }
                for r in rights
            ],
            "escalation_ladder": list(tenant_rights.ESCALATION_LADDER),
            "resources": [
                {"name": x.name, "what": x.what, "contact": x.contact, "url": x.url}
                for x in tenant_rights.RESOURCES
            ],
            "disclaimer": tenant_rights.DISCLAIMER,
        }

    # -- consolidated investigation brief (what the agents reason over) -
    def investigation_brief(self, rsn: str) -> dict[str, object] | None:
        report = self.report(rsn)
        if report is None:
            return None
        return {
            "report": report.model_dump(mode="json"),
            "comparison": self.comparison(rsn),
            "neighbourhood": self.neighbourhood(report.ward_name) if report.ward_name else {},
            "rights": self.rights(rsn),
            "grounding": tenant_rights.grounding_context(report),
        }

    def city_stats(self) -> dict[str, object]:
        return self.store.city_stats()


@lru_cache(maxsize=1)
def get_service() -> HousingService:
    return HousingService()
