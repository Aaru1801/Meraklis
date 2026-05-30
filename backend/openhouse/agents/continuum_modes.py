"""The Agency Continuum — mode-decision logic & human-in-the-loop checkpoints.

Per the Agency Continuum framing, an agentic system should not be uniformly
autonomous. Each action sits somewhere on a spectrum, and the system must decide
*where* — acting on its own for low-stakes, reversible, high-confidence work, and
pausing for human validation when stakes or uncertainty are high.

Meraklis encodes three modes:

* **AUTONOMOUS** — the agent acts without asking (data fetch, cleaning,
  normalization, deterministic scoring). Low stakes, reversible, auditable.
* **AUTOMATED_RECOMMENDATION** — the agent produces advice the user simply
  reviews. Medium stakes; confident data.
* **HUMAN_VERIFICATION** — the agent pauses and presents findings with explicit
  checkpoints the user must confirm before acting. Triggered by high stakes
  (a High/Severe risk verdict that could change a housing decision), by legal
  advice, or by low-confidence / incomplete data.

``decide_for_advocacy`` returns the mode for a finished assessment;
``pipeline_modes`` documents the mode of every stage; ``DECISION_MATRIX`` is the
human-readable rule set (a required deliverable).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..data.pio import PropertyIntelligenceObject

# Confidence below this is treated as "uncertain" → human verification.
CONFIDENCE_FLOOR = 0.5
HIGH_RISK_LEVELS = {"High", "Severe"}


class AgencyMode(str, Enum):
    AUTONOMOUS = "autonomous"
    AUTOMATED_RECOMMENDATION = "automated_recommendation"
    HUMAN_VERIFICATION = "human_verification"


class ContinuumDecision(BaseModel):
    """Where a given action/output sits on the agency continuum."""

    mode: AgencyMode
    stage: str
    stakes: str  # low | medium | high
    confidence: float
    rationale: str
    checkpoints: list[str] = Field(
        default_factory=list, description="HITL prompts the user should confirm before acting"
    )
    requires_user_action: bool = False


# ---------------------------------------------------------------------------
# The decision matrix (deliverable): documents the rule for each stage.
# ---------------------------------------------------------------------------
DECISION_MATRIX: list[dict] = [
    {
        "stage": "Data ingestion (RentSafeTO / open data fetch)",
        "default_mode": AgencyMode.AUTONOMOUS.value,
        "stakes": "low",
        "rule": "Always autonomous — fetching public data is reversible and auditable.",
        "escalates_when": "Never (read-only).",
    },
    {
        "stage": "Address normalization & record reconciliation",
        "default_mode": AgencyMode.AUTONOMOUS.value,
        "stakes": "low",
        "rule": "Autonomous when match score ≥ 0.7.",
        "escalates_when": "Match score in 0.5–0.7 band → flag the record as an approximate match.",
    },
    {
        "stage": "Deterministic risk scoring",
        "default_mode": AgencyMode.AUTONOMOUS.value,
        "stakes": "low",
        "rule": "Autonomous — pure, explainable arithmetic over published data.",
        "escalates_when": "Never (deterministic & transparent).",
    },
    {
        "stage": "AI risk interpretation (Research agent)",
        "default_mode": AgencyMode.AUTOMATED_RECOMMENDATION.value,
        "stakes": "medium",
        "rule": "Recommendation the user reviews; grounded strictly in the data.",
        "escalates_when": "Source confidence < 0.5 or many obstructed/uninspected areas.",
    },
    {
        "stage": "High/Severe risk warning on a specific building",
        "default_mode": AgencyMode.HUMAN_VERIFICATION.value,
        "stakes": "high",
        "rule": "Always present for user validation — it can change a housing decision.",
        "escalates_when": "Always (high stakes).",
    },
    {
        "stage": "Legal / tenant-rights advice",
        "default_mode": AgencyMode.HUMAN_VERIFICATION.value,
        "stakes": "high",
        "rule": "Always framed as information to verify with a clinic/hotline, never as a final legal opinion.",
        "escalates_when": "Always (legal stakes).",
    },
    {
        "stage": "Low-confidence or incomplete assessment",
        "default_mode": AgencyMode.HUMAN_VERIFICATION.value,
        "stakes": "high",
        "rule": "Pause and ask the user to verify identity/conditions before relying on it.",
        "escalates_when": "Overall confidence < 0.5 or the building could not be resolved.",
    },
]


def pipeline_modes() -> list[ContinuumDecision]:
    """The fixed per-stage modes of the Meraklis pipeline (for transparency)."""
    return [
        ContinuumDecision(
            mode=AgencyMode(row["default_mode"]),
            stage=row["stage"],
            stakes=row["stakes"],
            confidence=1.0 if row["default_mode"] == AgencyMode.AUTONOMOUS.value else 0.0,
            rationale=row["rule"],
            requires_user_action=row["default_mode"] == AgencyMode.HUMAN_VERIFICATION.value,
        )
        for row in DECISION_MATRIX
    ]


def decide_for_advocacy(pio: PropertyIntelligenceObject) -> ContinuumDecision:
    """Decide the agency mode for a completed advocacy assessment."""
    confidence = pio.overall_confidence
    risk_level = pio.risk.risk_level if pio.risk else "Unknown"

    # 1) Uncertain / unresolved data → human verification.
    if not pio.resolved or confidence < CONFIDENCE_FLOOR:
        return ContinuumDecision(
            mode=AgencyMode.HUMAN_VERIFICATION,
            stage="advocacy",
            stakes="high",
            confidence=confidence,
            rationale=(
                "Meraklis could not confidently identify this building or key data is "
                "missing/uncertain, so it should not present a firm verdict without your input."
            ),
            requires_user_action=True,
            checkpoints=[
                "Confirm the exact address (and unit) — the match may be approximate.",
                "Treat this as a preliminary view; verify conditions in person.",
            ]
            + [u for u in pio.uncertainties[:3]],
        )

    # 2) High/Severe risk → human verification (high stakes).
    if risk_level in HIGH_RISK_LEVELS:
        checkpoints = [
            "Review each red flag below and confirm you understand the safety implications "
            "before viewing or signing.",
            "Verify the most serious issues in person — City inspection data can lag real "
            "conditions.",
            "Before committing, get free advice from the FMTA Tenant Hotline (416-921-9494) "
            "or a community legal clinic.",
        ]
        if pio.risk and pio.risk.newcomer_lens:
            checkpoints.extend(pio.risk.newcomer_lens.questions_to_ask[:2])
        return ContinuumDecision(
            mode=AgencyMode.HUMAN_VERIFICATION,
            stage="advocacy",
            stakes="high",
            confidence=confidence,
            rationale=(
                f"This is a {risk_level}-risk verdict that could change your housing decision, "
                "so Meraklis presents it for your validation rather than acting on it for you."
            ),
            requires_user_action=True,
            checkpoints=checkpoints,
        )

    # 3) Otherwise → automated recommendation the user reviews.
    return ContinuumDecision(
        mode=AgencyMode.AUTOMATED_RECOMMENDATION,
        stage="advocacy",
        stakes="medium",
        confidence=confidence,
        rationale=(
            f"Data is sufficiently confident and the risk level is {risk_level}; Meraklis "
            "offers this as a recommendation for you to review."
        ),
        requires_user_action=False,
        checkpoints=[
            "Skim the concerns and confirm they match what you see in person.",
        ],
    )
