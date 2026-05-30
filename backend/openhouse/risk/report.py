"""Pydantic models for the OpenHouse risk report.

These models are the contract shared by the risk engine, the FastAPI layer,
the Continuum agents, and (eventually) the frontend — so they're kept
deliberately explicit and JSON-friendly.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    MINOR = "minor"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"critical": 4, "high": 3, "moderate": 2, "minor": 1, "info": 0}[self.value]


class RedFlag(BaseModel):
    """A specific, evidence-backed concern about a building."""

    code: str = Field(description="Stable id, e.g. 'poor:COMMON AREA PESTS' or 'derived:reactive'")
    title: str
    detail: str = Field(description="Plain-language explanation of why it matters to a tenant")
    severity: Severity
    group: str | None = None
    newcomer_relevant: bool = False
    category_key: str | None = None
    score: int | None = None
    evidence: str | None = Field(default=None, description="The raw datapoint behind the flag")


class GroupScore(BaseModel):
    """Roll-up of one thematic group (Security, Pests, …)."""

    group: str
    subscore: int | None = Field(default=None, description="0-100; higher is better")
    status: str = "unknown"  # good | adequate | poor | unknown
    n_categories: int = 0
    n_poor: int = 0
    n_not_assessed: int = 0


class TrendInfo(BaseModel):
    direction: str = "unknown"  # improving | declining | stable | unknown
    delta: int | None = None
    from_year: int | None = None
    to_year: int | None = None
    history: list[dict] = Field(default_factory=list)  # [{year, score}]
    narrative: str = ""


class Strength(BaseModel):
    title: str
    group: str | None = None


class NewcomerLens(BaseModel):
    """The newcomer-specific view: what matters most to someone new to Toronto."""

    risk_score: int = Field(description="0-100; higher is riskier for a newcomer")
    risk_level: str
    summary: str
    priorities: list[RedFlag] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)


class RiskReport(BaseModel):
    """The full deterministic risk assessment for a building."""

    rsn: str
    address: str
    ward_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    units: int | None = None
    storeys: int | None = None
    year_built: int | None = None
    property_type: str | None = None

    overall_score: int | None = Field(default=None, description="City RentSafeTO score, 0-100")
    grade: str = "N/A"  # A-F
    risk_level: str = "Unknown"  # Low | Moderate | Elevated | High | Severe
    risk_score: int = 0  # 0-100, higher = riskier (OpenHouse composite)

    summary_line: str = ""
    headline_factors: list[str] = Field(default_factory=list)

    red_flags: list[RedFlag] = Field(default_factory=list)
    not_assessed: list[RedFlag] = Field(default_factory=list)
    strengths: list[Strength] = Field(default_factory=list)
    group_breakdown: list[GroupScore] = Field(default_factory=list)

    newcomer_lens: NewcomerLens | None = None
    trend: TrendInfo = Field(default_factory=TrendInfo)

    evaluation_date: dt.date | None = None
    n_evaluations: int = 0

    data_source: str = (
        "City of Toronto Open Data — RentSafeTO Apartment Building Evaluations"
    )
    disclaimer: str = (
        "This report is generated from public City of Toronto inspection data for "
        "general information only. It is not legal advice and reflects building "
        "conditions as of the last municipal evaluation, which may have changed."
    )
