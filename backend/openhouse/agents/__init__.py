"""Agentic layer for Meraklis Edge.

Local-first by default: the Edge investigator uses an OpenAI-compatible local
model when one is reachable and deterministic fallbacks when it is not. No
cloud AI provider is configured anywhere.
"""

from .continuum_modes import (
    DECISION_MATRIX,
    AgencyMode,
    ContinuumDecision,
    decide_for_advocacy,
    pipeline_modes,
)
from .edge import (
    DEMO_ADDRESSES,
    PIPELINE_STAGES,
    EdgeInvestigationRequest,
    EdgeInvestigationResponse,
    EdgeInvestigator,
    get_edge_investigator,
)
from .schemas import AdvocacyReport, ResearchFindings, UserProfile
from .service import HousingService, get_service

__all__ = [
    "EdgeInvestigator",
    "EdgeInvestigationRequest",
    "EdgeInvestigationResponse",
    "get_edge_investigator",
    "DEMO_ADDRESSES",
    "PIPELINE_STAGES",
    "HousingService",
    "get_service",
    "AdvocacyReport",
    "ResearchFindings",
    "UserProfile",
    "AgencyMode",
    "ContinuumDecision",
    "decide_for_advocacy",
    "pipeline_modes",
    "DECISION_MATRIX",
]
