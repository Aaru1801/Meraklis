"""The canonical Property Intelligence Object (PIO).

A single, schema-standardized object that encapsulates everything OpenHouse
knows about a building/unit, fused from every source adapter — with explicit
per-source provenance, an overall confidence score, a data-completeness measure,
and a list of surfaced uncertainties. This is the object the Advocate agent and
the UI consume.
"""

from __future__ import annotations

import asyncio
import datetime as dt

from pydantic import BaseModel, Field

from ..risk.report import RiskReport
from .adapters.base import AddressQuery, SourceAdapter, SourceStatus
from .adapters.market import HouseSigmaAdapter, RealtorCaAdapter
from .adapters.massing import MassingAdapter
from .adapters.rentsafeto_adapter import RentSafeToAdapter
from .address import normalize_address
from .rent import estimate_rent

# Typical residential floor-to-floor heights (m) — used only to translate a
# 3D-Massing roof height into an *approximate* storey range for the cross-check.
_FLOOR_TALL = 3.4
_FLOOR_SHORT = 2.9


class SourceProvenance(BaseModel):
    source: str
    status: str
    confidence: float
    note: str = ""
    fetched_at: str | None = None


class MassingCrossCheck(BaseModel):
    """Independent height check: City 3D Massing vs RentSafeTO storey count."""

    rentsafeto_storeys: int | None = None
    implied_storeys_low: int | None = None
    implied_storeys_high: int | None = None
    status: str = "unknown"  # consistent | differs | unknown
    note: str = ""


class MassingInfo(BaseModel):
    """City of Toronto 3D Massing: footprint geometry + building height."""

    matched: bool = False
    source: str = "City of Toronto Open Data — 3D Massing"
    source_url: str = "https://open.toronto.ca/dataset/3d-massing/"
    massing_year: int | None = None
    distance_m: float | None = None
    min_height_m: float | None = None
    avg_height_m: float | None = None
    max_height_m: float | None = None
    surface_elev_m: float | None = None
    height_source: str | None = None
    footprint_area_m2: float | None = None
    n_vertices: int | None = None
    centroid: dict | None = None
    # Exterior ring in local ground-metres relative to the centroid (for rendering).
    footprint_m: list[list[float]] = Field(default_factory=list)
    cross_check: MassingCrossCheck | None = None


class MarketIntel(BaseModel):
    """Listing/market data, when available from a listing adapter."""

    listed: bool | None = None
    status: str | None = None  # for_rent | for_sale | sold | off_market | estimate
    list_price: int | None = None
    monthly_rent: int | None = None  # estimated or listed monthly rent
    rent_low: int | None = None
    rent_high: int | None = None
    bedrooms: float | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    url: str | None = None
    as_of: str | None = None
    source: str | None = None
    confidence: float = 0.0
    is_estimate: bool = False  # True = modeled, not a real listing
    basis: str | None = None


class PropertyIntelligenceObject(BaseModel):
    """Unified, multi-source intelligence for one building/unit."""

    # --- identity (normalized) ---
    address_raw: str = ""
    address_canonical: str = ""
    rsn: str | None = None
    ward_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    units: int | None = None
    storeys: int | None = None
    year_built: int | None = None
    property_type: str | None = None

    # --- safety intelligence (RentSafeTO) ---
    risk: RiskReport | None = None

    # --- market intelligence (Realtor.ca / HouseSigma, if provided) ---
    market: MarketIntel | None = None

    # --- 3D form (City of Toronto 3D Massing: footprint + height) ---
    massing: MassingInfo | None = None

    # --- meta ---
    provenance: list[SourceProvenance] = Field(default_factory=list)
    overall_confidence: float = 0.0
    data_completeness: float = 0.0
    uncertainties: list[str] = Field(default_factory=list)
    generated_at: str = ""

    @property
    def resolved(self) -> bool:
        return self.rsn is not None or self.risk is not None


class PIOBuilder:
    """Orchestrates the adapter layer into a PIO (concurrent, fault-tolerant)."""

    def __init__(self, adapters: list[SourceAdapter] | None = None):
        # RentSafeTO first: it sets identity + storeys that 3D Massing cross-checks.
        self.adapters = adapters or [
            RentSafeToAdapter(),
            RealtorCaAdapter(),
            HouseSigmaAdapter(),
            MassingAdapter(),
        ]

    async def build_async(self, query: AddressQuery) -> PropertyIntelligenceObject:
        # Concurrent, throttled, fault-tolerant fan-out. Each adapter.fetch is
        # already exception-safe, so gather never raises.
        results = await asyncio.gather(
            *(asyncio.to_thread(a.fetch, query) for a in self.adapters)
        )

        pio = PropertyIntelligenceObject(
            address_raw=query.raw_address,
            address_canonical=query.canonical_address
            or normalize_address(query.raw_address).canonical,
            generated_at=dt.datetime.now(dt.UTC).isoformat(),
        )

        total_sources = 0
        n_usable = 0
        primary_confidence = 0.0  # confidence in the safety assessment (RentSafeTO)
        best_usable_confidence = 0.0

        for res in results:
            pio.provenance.append(
                SourceProvenance(
                    source=res.source,
                    status=res.status.value,
                    confidence=res.confidence,
                    note=res.note,
                    fetched_at=res.fetched_at,
                )
            )
            total_sources += 1

            if res.source == "rentsafeto" and res.usable:
                self._merge_rentsafeto(pio, res.data)
                primary_confidence = res.confidence
                best_usable_confidence = max(best_usable_confidence, res.confidence)
                n_usable += 1
            elif res.usable and "market" in res.data:
                self._merge_market(pio, res.data["market"], res.source, res.confidence)
                best_usable_confidence = max(best_usable_confidence, res.confidence)
                n_usable += 1
            elif res.source == "toronto_3d_massing" and res.usable:
                # Enrichment + height cross-check only — never feeds the risk score.
                self._merge_massing(pio, res.data["massing"])
                n_usable += 1
            elif res.status in (SourceStatus.UNAVAILABLE, SourceStatus.ERROR, SourceStatus.UNCERTAIN):
                pio.uncertainties.append(f"{res.source}: {res.note}")

        # Derive a transparent rent estimate from the building's own RentSafeTO
        # record (location, age, size) when no real listing export is available.
        # It is attributed to RentSafeTO — the source it's actually derived from —
        # and is not counted as an independent source for confidence/completeness.
        if pio.market is None and pio.latitude is not None and pio.longitude is not None:
            est = estimate_rent(pio.latitude, pio.longitude, pio.year_built, pio.units, pio.storeys)
            if est:
                pio.market = MarketIntel(
                    status="estimate",
                    monthly_rent=est.monthly,
                    rent_low=est.low,
                    rent_high=est.high,
                    source="rentsafeto",
                    confidence=est.confidence,
                    is_estimate=True,
                    basis=(
                        "Estimated from this building's RentSafeTO record (location, age and "
                        "size) and Toronto average market rents. Not a live listing."
                    ),
                )

        # Overall confidence reflects the *primary* safety assessment (the verdict
        # the user acts on); data completeness reflects breadth across sources.
        pio.overall_confidence = round(primary_confidence or best_usable_confidence, 2)
        pio.data_completeness = round(n_usable / total_sources, 2) if total_sources else 0.0

        # Surface safety-data uncertainties from the risk report itself.
        if pio.risk:
            if pio.risk.not_assessed:
                pio.uncertainties.append(
                    f"rentsafeto: {len(pio.risk.not_assessed)} areas could not be inspected "
                    "(obstructed/refused) — those aspects are unknown."
                )
            if pio.risk.overall_score is None:
                pio.uncertainties.append("rentsafeto: no overall score on file for this building.")
        if pio.market is not None and pio.market.is_estimate:
            pio.uncertainties.append(
                "Rent shown is a modeled estimate from RentSafeTO data (no live Realtor.ca / "
                "HouseSigma listing) — verify the actual asking rent."
            )
        elif pio.market is None:
            pio.uncertainties.append("No market or rent data available for this building.")

        return pio

    def build(self, query: AddressQuery) -> PropertyIntelligenceObject:
        return asyncio.run(self.build_async(query))

    # ------------------------------------------------------------------
    @staticmethod
    def _merge_rentsafeto(pio: PropertyIntelligenceObject, data: dict) -> None:
        report = RiskReport.model_validate(data["report"])
        pio.risk = report
        pio.rsn = report.rsn
        pio.ward_name = report.ward_name
        pio.latitude = report.latitude
        pio.longitude = report.longitude
        pio.units = report.units
        pio.storeys = report.storeys
        pio.year_built = report.year_built
        pio.property_type = report.property_type
        if not pio.address_raw:
            pio.address_raw = report.address
        if report.address:
            pio.address_canonical = normalize_address(report.address).canonical

    @staticmethod
    def _merge_market(
        pio: PropertyIntelligenceObject, market: dict, source: str, confidence: float
    ) -> None:
        incoming = MarketIntel(
            listed=market.get("listed"),
            status=market.get("status"),
            list_price=market.get("list_price"),
            monthly_rent=market.get("monthly_rent"),
            rent_low=market.get("rent_low"),
            rent_high=market.get("rent_high"),
            bedrooms=market.get("bedrooms"),
            bathrooms=market.get("bathrooms"),
            sqft=market.get("sqft"),
            url=market.get("url"),
            as_of=market.get("as_of"),
            source=source,
            confidence=confidence,
            is_estimate=bool(market.get("is_estimate")),
            basis=market.get("basis"),
        )
        # Keep the higher-confidence market record if multiple sources respond.
        if pio.market is None or incoming.confidence > pio.market.confidence:
            pio.market = incoming

    @staticmethod
    def _merge_massing(pio: PropertyIntelligenceObject, m: dict) -> None:
        info = MassingInfo(
            matched=True,
            source=m.get("source") or "City of Toronto Open Data — 3D Massing",
            massing_year=m.get("massing_year"),
            distance_m=m.get("distance_m"),
            min_height_m=m.get("min_height_m"),
            avg_height_m=m.get("avg_height_m"),
            max_height_m=m.get("max_height_m"),
            surface_elev_m=m.get("surface_elev_m"),
            height_source=m.get("height_source"),
            footprint_area_m2=m.get("footprint_area_m2"),
            n_vertices=m.get("n_vertices"),
            centroid=m.get("centroid"),
            footprint_m=m.get("footprint_m", []),
        )
        # Independent cross-check against the RentSafeTO storey count (set above).
        info.cross_check = PIOBuilder._massing_cross_check(
            pio.storeys, info.avg_height_m, info.max_height_m
        )
        pio.massing = info
        if info.cross_check and info.cross_check.status == "differs":
            pio.uncertainties.append(
                "Building height: RentSafeTO storey count and the City 3D Massing model "
                "disagree — see the cross-check."
            )

    @staticmethod
    def _massing_cross_check(
        storeys: int | None, avg_h: float | None, max_h: float | None
    ) -> MassingCrossCheck:
        roof = max_h or avg_h
        floor_h = avg_h or max_h
        if not storeys or not roof:
            return MassingCrossCheck(
                rentsafeto_storeys=storeys,
                status="unknown",
                note="Not enough data to compare storey count with the 3D Massing height.",
            )
        # Translate the roof height into an approximate storey range (taller floors
        # → fewer storeys, shorter floors → more). Compare with ±1 storey slack.
        lo = int(round((floor_h or roof) / _FLOOR_TALL))
        hi = int(round(roof / _FLOOR_SHORT))
        lo, hi = min(lo, hi), max(lo, hi)
        # The avg→max spread already gives a generous band; no extra slack needed.
        consistent = lo <= storeys <= hi
        if consistent:
            note = (
                f"RentSafeTO records {storeys} storeys; the City 3D Massing roof height "
                f"(~{roof:.0f} m) implies roughly {lo}–{hi} storeys — consistent."
            )
        else:
            note = (
                f"RentSafeTO records {storeys} storeys, but the City 3D Massing model shows a "
                f"~{roof:.0f} m structure (≈{lo}–{hi} storeys) — a cross-source discrepancy "
                "worth verifying."
            )
        return MassingCrossCheck(
            rentsafeto_storeys=storeys,
            implied_storeys_low=lo,
            implied_storeys_high=hi,
            status="consistent" if consistent else "differs",
            note=note,
        )


_builder: PIOBuilder | None = None


def get_pio_builder() -> PIOBuilder:
    global _builder
    if _builder is None:
        _builder = PIOBuilder()
    return _builder
