"""Typed domain models for RentSafeTO building-evaluation data.

The City's CKAN datastore returns every value as a string (or occasionally a
bare int), with ``"N/A"`` for inapplicable inspection categories and empty
strings for missing numbers. ``Evaluation.from_ckan`` does all the defensive
parsing in one place so the rest of the codebase works with clean, typed data.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

from .categories import ALL_CATEGORY_KEYS, BY_KEY, Group


def _to_int(value: Any) -> int | None:
    """Best-effort int parse; returns None for ``""``, ``"N/A"``, junk."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if not s or s.upper() in {"N/A", "NA", "NONE", "-"}:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"N/A", "NA", "NONE", "-"}:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# The pre-2023 CKAN resource uses underscored column names, a different score
# field, and a coarser category set. We map its core fields onto the canonical
# (spaced) names so a single parser handles both. The coarse pre-2023 category
# columns are intentionally left unmapped — they don't align with the granular
# 2023+ taxonomy, so those rows contribute to the *score-history timeline* only,
# not to the per-category breakdown.
_PRE2023_FIELD_MAP: dict[str, str] = {
    "YEAR_REGISTERED": "YEAR REGISTERED",
    "YEAR_EVALUATED": "YEAR EVALUATED",
    "YEAR_BUILT": "YEAR BUILT",
    "PROPERTY_TYPE": "PROPERTY TYPE",
    "SITE_ADDRESS": "SITE ADDRESS",
    "CONFIRMED_STOREYS": "CONFIRMED STOREYS",
    "CONFIRMED_UNITS": "CONFIRMED UNITS",
    "EVALUATION_COMPLETED_ON": "EVALUATION COMPLETED ON",
    "SCORE": "CURRENT BUILDING EVAL SCORE",
    "NO_OF_AREAS_EVALUATED": "NO OF AREAS EVALUATED",
}


def _normalize_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Map a raw CKAN record onto canonical (spaced) column names.

    Records from the 2023+ resource already use the canonical names and pass
    through unchanged. Pre-2023 records (detected by ``SITE_ADDRESS``) are
    remapped. ``RSN``, ``WARD``, ``WARDNAME``, ``LATITUDE``, ``LONGITUDE`` are
    identical across both schemas.
    """
    if "SITE_ADDRESS" not in rec and "YEAR_EVALUATED" not in rec:
        return rec  # already canonical (2023+ schema)
    out = dict(rec)
    for src, dst in _PRE2023_FIELD_MAP.items():
        if src in rec and dst not in out:
            out[dst] = rec[src]
    return out


def _to_date(value: Any) -> dt.date | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # CKAN returns ISO-ish strings: "2024-10-08" or "2024-10-08T00:00:00".
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


class CategoryScore(BaseModel):
    """One inspection category's score for a building, with tenant context."""

    key: str
    label: str
    group: str
    # 3 = good, 2 = adequate, 1 = poor/deficiency, 0 = obstructed/refused
    # (inspector could not assess), None = not applicable to this building.
    score: int | None
    weight: int
    newcomer_critical: bool
    tenant_impact: str

    @property
    def is_poor(self) -> bool:
        """A confirmed deficiency (graded 1)."""
        return self.score == 1

    @property
    def is_not_assessed(self) -> bool:
        """Obstructed or access refused during inspection (graded 0)."""
        return self.score == 0

    @property
    def is_good(self) -> bool:
        return self.score == 3

    @property
    def is_concern(self) -> bool:
        """Poor, or unverifiable due to obstruction/refusal."""
        return self.score in (0, 1)

    @property
    def status(self) -> str:
        return {
            3: "good",
            2: "adequate",
            1: "poor",
            0: "not_assessed",
        }.get(self.score, "not_applicable")


class Evaluation(BaseModel):
    """A single RentSafeTO evaluation of a building (one dataset row)."""

    rsn: str = Field(description="RentSafeTO unique building id")
    address: str
    ward: str | None = None
    ward_name: str | None = None
    property_type: str | None = None

    year_built: int | None = None
    year_registered: int | None = None
    year_evaluated: int | None = None
    evaluation_completed_on: dt.date | None = None

    storeys: int | None = None
    units: int | None = None

    score: int | None = Field(default=None, description="Overall eval score 0-100")
    proactive_score: int | None = None
    reactive_score: int | None = Field(
        default=None,
        description="Reflects outstanding work orders / complaints; >0 is a flag",
    )
    areas_evaluated: int | None = None

    latitude: float | None = None
    longitude: float | None = None

    # Raw per-category scores, keyed by the exact CKAN column name.
    categories: dict[str, int | None] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    @classmethod
    def from_ckan(cls, raw: dict[str, Any]) -> "Evaluation":
        """Parse one raw CKAN datastore record (either schema) into an Evaluation.

        Granular per-category scores are extracted *only* from 2023+ records.
        The pre-2023 resource uses a coarser category set on a different scale
        (and even reuses a column name like ``GRAFFITI`` with different values),
        so those rows contribute to the score-history timeline only.
        """
        is_pre2023 = "SITE_ADDRESS" in raw or "YEAR_EVALUATED" in raw
        rec = _normalize_record(raw)
        cats: dict[str, int | None] = {}
        if not is_pre2023:
            for key in ALL_CATEGORY_KEYS:
                if key in rec:
                    cats[key] = _to_int(rec[key])

        return cls(
            rsn=str(rec.get("RSN", "")).strip(),
            address=str(rec.get("SITE ADDRESS", "")).strip(),
            ward=(str(rec["WARD"]).strip() if rec.get("WARD") not in (None, "") else None),
            ward_name=(
                str(rec["WARDNAME"]).strip() if rec.get("WARDNAME") not in (None, "") else None
            ),
            property_type=(
                str(rec["PROPERTY TYPE"]).strip()
                if rec.get("PROPERTY TYPE") not in (None, "")
                else None
            ),
            year_built=_to_int(rec.get("YEAR BUILT")),
            year_registered=_to_int(rec.get("YEAR REGISTERED")),
            year_evaluated=_to_int(rec.get("YEAR EVALUATED")),
            evaluation_completed_on=_to_date(rec.get("EVALUATION COMPLETED ON")),
            storeys=_to_int(rec.get("CONFIRMED STOREYS")),
            units=_to_int(rec.get("CONFIRMED UNITS")),
            score=_to_int(rec.get("CURRENT BUILDING EVAL SCORE")),
            proactive_score=_to_int(rec.get("PROACTIVE BUILDING SCORE")),
            reactive_score=_to_int(rec.get("CURRENT REACTIVE SCORE")),
            areas_evaluated=_to_int(rec.get("NO OF AREAS EVALUATED")),
            latitude=_to_float(rec.get("LATITUDE")),
            longitude=_to_float(rec.get("LONGITUDE")),
            categories=cats,
        )

    # ------------------------------------------------------------------
    def category_scores(self) -> list[CategoryScore]:
        """Enriched category scores (recognized categories only), in taxonomy order."""
        out: list[CategoryScore] = []
        for key, cat in BY_KEY.items():
            if key not in self.categories:
                continue
            out.append(
                CategoryScore(
                    key=key,
                    label=cat.label,
                    group=cat.group.value,
                    score=self.categories[key],
                    weight=cat.weight,
                    newcomer_critical=cat.newcomer_critical,
                    tenant_impact=cat.tenant_impact,
                )
            )
        return out

    @property
    def has_reactive_issues(self) -> bool:
        return bool(self.reactive_score and self.reactive_score > 0)

    @property
    def building_age(self) -> int | None:
        if self.year_built and self.year_evaluated:
            return max(0, self.year_evaluated - self.year_built)
        return None


class Building(BaseModel):
    """A building identified by RSN, with its most-recent evaluation and history."""

    rsn: str
    address: str
    ward: str | None = None
    ward_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    storeys: int | None = None
    units: int | None = None
    year_built: int | None = None

    current: Evaluation
    history: list[Evaluation] = Field(default_factory=list)

    @classmethod
    def from_evaluations(cls, evals: list[Evaluation]) -> "Building":
        """Build from one-or-more evaluations of the same RSN (newest first)."""
        ordered = sorted(
            evals,
            key=lambda e: (e.evaluation_completed_on or dt.date.min, e.year_evaluated or 0),
            reverse=True,
        )
        current = ordered[0]
        return cls(
            rsn=current.rsn,
            address=current.address,
            ward=current.ward,
            ward_name=current.ward_name,
            latitude=current.latitude,
            longitude=current.longitude,
            storeys=current.storeys,
            units=current.units,
            year_built=current.year_built,
            current=current,
            history=ordered[1:],
        )

    @property
    def score_trend(self) -> int | None:
        """Change in overall score from the previous evaluation to the current one."""
        if not self.history:
            return None
        prev = next((e for e in self.history if e.score is not None), None)
        if prev is None or self.current.score is None:
            return None
        return self.current.score - prev.score


class BuildingSummary(BaseModel):
    """Lightweight building record for search results and map pins."""

    rsn: str
    address: str
    ward_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    units: int | None = None
    storeys: int | None = None
    year_built: int | None = None
    score: int | None = None
    grade: str | None = None
    risk_level: str | None = None
    estimated_rent: int | None = None  # modeled monthly rent (see openhouse.data.rent)
    value_index: int | None = None  # 0-100, higher = better value for condition
    value_band: str | None = None  # good_value | fair | rich | overpriced
