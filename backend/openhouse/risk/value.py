"""Value-for-risk — is a building's rent fair for its *condition*? (deterministic)

RentSafeTO carries no rent figure. This module pairs the transparent rent
*estimate* (:mod:`openhouse.data.rent`) with the City condition score + red flags
to answer a consumer-fairness question:

    "For a building in this condition, is the typical asking rent high or low?"

The market rent estimate is driven by location and age — it does **not** know the
building's condition. So two buildings of similar age in the same area get a
similar market estimate even if one is well-kept (high City score) and one is
troubled (low score, many red flags). We therefore derive a *condition-fair
rent* — the market estimate discounted for poor condition (or given a small
premium for excellent condition) — and report the gap.

It is clearly labelled an **estimate / market-fairness signal**, never a live
price and never financial advice, and it **never affects the risk score**.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..data.rent import estimate_rent
from .report import RiskReport, Severity

# A typical, well-kept Toronto RentSafeTO building scores around here (dataset
# mean ≈ 88). At the reference, condition neither adds nor subtracts rent.
_REFERENCE_SCORE = 87
_MAX_DISCOUNT = 0.24  # worst condition → fair rent up to 24% below area-typical
_MAX_PREMIUM = 0.06   # best condition → fair rent up to 6% above


def _round25(x: float) -> int:
    return int(round(x / 25.0) * 25)


def _condition_multiplier(score: int | None, n_serious: int = 0) -> float:
    """How much a building's condition should bend its rent vs. area-typical."""
    s = _REFERENCE_SCORE if score is None else score
    if s >= _REFERENCE_SCORE:
        c = 1.0 + min(_MAX_PREMIUM, 0.004 * (s - _REFERENCE_SCORE))
    else:
        c = 1.0 - min(0.20, 0.0072 * (_REFERENCE_SCORE - s))
    # serious safety/essential deficiencies are risk a renter would absorb.
    c -= min(0.10, 0.015 * n_serious)
    return max(1.0 - _MAX_DISCOUNT, min(1.0 + _MAX_PREMIUM, c))


def _band(gap_pct: float) -> tuple[str, str]:
    """Map an over/under-payment percentage to a (band, verdict)."""
    if gap_pct >= 10:
        return "overpriced", "Overpriced for its condition"
    if gap_pct >= 4:
        return "rich", "A bit rich for its condition"
    if gap_pct > -4:
        return "fair", "Fairly priced for its condition"
    return "good_value", "Good value for its condition"


def _index_from_gap(gap_pct: float) -> int:
    """0-100 value index (higher = better value for condition; 50 = fair)."""
    return max(0, min(100, round(50 - gap_pct * 2.5)))


def value_index_for(score: int | None) -> int:
    """Lightweight, score-only value index for the city map (no red-flag term).

    At the map level we only have the City score; the full per-building signal
    (with red flags and the rent comparison) is computed by :func:`value_for_risk`.
    """
    c = _condition_multiplier(score)
    gap_pct = (1.0 - c) / c * 100.0
    return _index_from_gap(gap_pct)


def value_band_for(score: int | None) -> str:
    c = _condition_multiplier(score)
    return _band((1.0 - c) / c * 100.0)[0]


class ValueForRisk(BaseModel):
    """Whether a building's rent looks high or low for its condition."""

    available: bool = True
    market_rent: int | None = None          # location/age estimate (area-typical)
    market_low: int | None = None
    market_high: int | None = None
    condition_fair_rent: int | None = None   # market estimate adjusted for condition
    asking_rent: int | None = None           # optional, user-supplied real asking rent
    reference_rent: int | None = None        # what we judged against (asking if given, else market)
    gap_monthly: int = 0                     # reference − fair (+over / −under)
    gap_pct: float = 0.0
    annual_gap: int = 0
    band: str = "fair"                       # good_value | fair | rich | overpriced
    verdict: str = ""
    value_index: int = 50                    # 0-100, higher = better value for condition
    rationale: str = ""
    drivers: list[str] = Field(default_factory=list)
    basis: str = ""
    is_estimate: bool = True
    disclaimer: str = (
        "Rent is a transparent model estimate (not a live listing). This is a "
        "market-fairness signal for the building's condition, not financial advice, "
        "and it never affects the risk score."
    )


def value_for_risk(risk: RiskReport | None, asking_rent: int | None = None) -> ValueForRisk:
    """Compute the value-for-risk signal for a building (pure, offline, no LLM)."""
    if risk is None:
        return ValueForRisk(available=False, rationale="No risk report available.")
    est = estimate_rent(risk.latitude, risk.longitude, risk.year_built, risk.units, risk.storeys)
    if est is None:
        return ValueForRisk(
            available=False,
            rationale="Building could not be geolocated, so no rent estimate is available.",
        )

    n_serious = sum(
        1 for f in risk.red_flags if f.severity in (Severity.CRITICAL, Severity.HIGH)
    )
    c = _condition_multiplier(risk.overall_score, n_serious)
    fair = _round25(est.monthly * c)
    reference = asking_rent if asking_rent else est.monthly
    gap_monthly = reference - fair
    gap_pct = round(100.0 * gap_monthly / fair, 1) if fair else 0.0
    band, verdict = _band(gap_pct)

    drivers: list[str] = []
    if risk.overall_score is not None:
        drivers.append(f"City score {risk.overall_score}/100 (Grade {risk.grade})")
    if n_serious:
        drivers.append(f"{n_serious} serious red flag(s) a renter would absorb")
    drivers.append(f"≈${est.monthly:,}/mo area-typical for the location & building age")

    discount_pct = round((1.0 - c) * 100.0, 1)
    if asking_rent:
        direction = "above" if gap_monthly > 0 else "below"
        rationale = (
            f"For its condition, a fair rent is about ${fair:,}/mo. The asking rent you "
            f"entered (${asking_rent:,}/mo) is ${abs(gap_monthly):,}/mo "
            f"({abs(gap_pct):.0f}%) {direction} that — about ${abs(gap_monthly) * 12:,}/yr."
        )
    else:
        less_more = "less" if discount_pct >= 0 else "more"
        tail = (
            "Paying the area-typical rate would mean overpaying for its condition."
            if band in ("overpriced", "rich")
            else "It is priced in line with — or below — what its condition warrants."
        )
        rationale = (
            f"A well-kept building in this area rents for about ${est.monthly:,}/mo. Given "
            f"this building's condition, a fair rent is about ${fair:,}/mo "
            f"(~{abs(discount_pct):.0f}% {less_more}). {tail}"
        )

    return ValueForRisk(
        available=True,
        market_rent=est.monthly,
        market_low=est.low,
        market_high=est.high,
        condition_fair_rent=fair,
        asking_rent=asking_rent,
        reference_rent=reference,
        gap_monthly=gap_monthly,
        gap_pct=gap_pct,
        annual_gap=gap_monthly * 12,
        band=band,
        verdict=verdict,
        value_index=_index_from_gap(gap_pct),
        rationale=rationale,
        drivers=drivers,
        basis=est.basis,
    )
