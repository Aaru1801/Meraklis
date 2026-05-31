"""Pydantic schemas for the agent pipeline I/O.

``UserProfile`` lets the Advocate tailor advice to a real household. The
``AdvocacyReport`` is the structured product the Advocate agent emits and the
API returns — designed so the frontend can render rich, sectioned guidance.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Optional context about the renter, for personalized advice."""

    household_size: int | None = Field(default=None, ge=1)
    has_children: bool | None = None
    has_seniors: bool | None = None
    has_mobility_needs: bool | None = None
    budget_max_monthly: int | None = Field(default=None, description="CAD/month")
    languages: list[str] = Field(default_factory=list)
    is_newcomer: bool = True
    priorities: list[str] = Field(
        default_factory=list,
        description="e.g. ['safety', 'heat', 'pests', 'quiet', 'near transit']",
    )
    notes: str | None = None
    respond_language: str | None = Field(
        default=None,
        description="Language for renter-facing guidance, e.g. 'Simplified Chinese'. None = English.",
    )

    def to_prompt(self) -> str:
        if self.model_dump(exclude_none=True, exclude_defaults=True) == {} and not self.priorities:
            return "No specific household details were provided; give guidance for a typical newcomer renter."
        bits: list[str] = []
        if self.is_newcomer:
            bits.append("The renter is a newcomer to Toronto / Canada.")
        if self.household_size:
            bits.append(f"Household size: {self.household_size}.")
        if self.has_children:
            bits.append("There are children in the household.")
        if self.has_seniors:
            bits.append("There are seniors in the household.")
        if self.has_mobility_needs:
            bits.append("Someone has mobility needs (stairs/elevators matter).")
        if self.budget_max_monthly:
            bits.append(f"Maximum budget ~${self.budget_max_monthly}/month.")
        if self.languages:
            bits.append(f"Preferred languages: {', '.join(self.languages)}.")
        if self.priorities:
            bits.append(f"Stated priorities: {', '.join(self.priorities)}.")
        if self.notes:
            bits.append(f"Additional notes: {self.notes}")
        if self.respond_language:
            bits.append(f"Renter-facing guidance must be written in {self.respond_language}.")
        return " ".join(bits)


class ResearchFindings(BaseModel):
    """Structured output of the Research agent."""

    summary: str = Field(description="2-4 sentence synthesis of what the data shows")
    severity_assessment: str = Field(description="How serious, and why, in plain terms")
    notable_patterns: list[str] = Field(
        default_factory=list, description="Concrete patterns/datapoints worth highlighting"
    )
    neighbourhood_context: str = Field(
        default="", description="How this building compares within its ward"
    )
    legal_topics: list[str] = Field(
        default_factory=list, description="Tenant-rights topics implicated (heat, pests, …)"
    )


class Concern(BaseModel):
    title: str
    why_it_matters: str
    severity: str  # critical | high | moderate | minor


class RightSummary(BaseModel):
    title: str
    summary: str
    action: str


class SchoolNearby(BaseModel):
    name: str
    type: str = ""
    address: str = ""
    distance_m: int = 0


class AdvocacyReport(BaseModel):
    """The Advocate agent's final, personalized output."""

    rsn: str
    address: str
    risk_level: str
    grade: str
    overall_score: int | None = None

    headline: str = Field(description="One-paragraph plain-language verdict")
    bottom_line: str = Field(description="The single most important takeaway for this renter")

    key_concerns: list[Concern] = Field(default_factory=list)
    what_this_means_for_you: str = Field(
        default="", description="Advice tailored to the renter's profile"
    )
    your_rights: list[RightSummary] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    questions_before_signing: list[str] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)
    # Family context: nearby schools, populated when the profile has children.
    schools_nearby: list[SchoolNearby] = Field(default_factory=list)

    generated_by: str = "deterministic"  # "ai" or "deterministic"
    limitations: str = ""
    disclaimer: str = ""

    # --- Agency Continuum (HITL) ---
    continuum_mode: str = "automated_recommendation"  # autonomous | automated_recommendation | human_verification
    agency_stakes: str = "medium"
    agency_rationale: str = ""
    verification_checkpoints: list[str] = Field(default_factory=list)

    # --- data trust (from the PIO) ---
    data_confidence: float = 0.0
    data_completeness: float = 0.0
    uncertainties: list[str] = Field(default_factory=list)
