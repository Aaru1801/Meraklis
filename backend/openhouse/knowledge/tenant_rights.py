"""Ontario / Toronto tenant-rights knowledge base.

Every fact here was verified against primary sources (Ontario's *Residential
Tenancies Act, 2006*, the City of Toronto bylaws, the Landlord and Tenant Board,
and the Federation of Metro Tenants' Associations) in May 2026 — see the
``source`` fields. This module has two jobs:

1. **Ground the Advocate agent.** ``grounding_context(report)`` assembles a
   compact, accurate brief tied to a building's actual red flags, which is fed
   to the LLM as authoritative context so legal information is cited, not
   invented.
2. **Power a user-facing rights section** via ``relevant_rights(report)``.

This is legal *information*, not legal advice. The disclaimer is attached
everywhere it surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..risk.report import RiskReport

DISCLAIMER = (
    "This is general legal information for Ontario tenants, not legal advice. "
    "Laws and timelines change and every situation is different. For advice on "
    "your situation, contact a community legal clinic, the Federation of Metro "
    "Tenants' Associations, or a licensed paralegal/lawyer."
)


@dataclass(frozen=True, slots=True)
class Right:
    """One tenant right / landlord obligation and how to act on it."""

    topic: str
    title: str
    right: str
    legal_basis: str
    source: str
    what_you_can_do: tuple[str, ...]
    escalation: str


# ---------------------------------------------------------------------------
# Core rights, keyed by topic.
# ---------------------------------------------------------------------------
RIGHTS: dict[str, Right] = {
    "heat": Right(
        topic="heat",
        title="Heat in winter",
        right=(
            "Your landlord must keep your unit at a minimum of 21°C during the "
            "heating season — October 1 to May 15 — even if you pay your own "
            "utilities. Heat is a 'vital service' that cannot be withheld."
        ),
        legal_basis=(
            "Residential Tenancies Act, 2006 s.21 (vital services); City of "
            "Toronto Municipal Code Ch.497 (Heating) — minimum 21°C, Oct 1–May 15."
        ),
        source=(
            "ontario.ca/laws/statute/06r17 (s.21); toronto.ca — Indoor "
            "Temperatures in Apartment Units"
        ),
        what_you_can_do=(
            "Measure and log the temperature with date and time (photos of a "
            "thermometer help).",
            "Tell your landlord in writing (text/email counts) and keep a copy.",
            "If it isn't fixed, call 311 — the City can inspect and order the "
            "landlord to provide heat.",
            "You can apply to the Landlord and Tenant Board (Form T2 and/or T6) "
            "for an order and a rent abatement.",
        ),
        escalation="Document → written notice → City 311 → LTB application (T2/T6).",
    ),
    "vital_services": Right(
        topic="vital_services",
        title="Water, electricity & gas",
        right=(
            "A landlord cannot withhold or deliberately interfere with vital "
            "services — hot and cold water, electricity, fuel and gas — during "
            "your tenancy."
        ),
        legal_basis="Residential Tenancies Act, 2006 s.21.",
        source="ontario.ca/laws/statute/06r17 (s.21)",
        what_you_can_do=(
            "Document each outage (dates, duration, photos).",
            "Notify the landlord in writing immediately.",
            "Call 311 for City enforcement; call your utility for safety issues.",
            "Apply to the LTB (T2) — interfering with vital services is a serious "
            "breach.",
        ),
        escalation="Document → written notice → City 311 → LTB T2.",
    ),
    "repairs": Right(
        topic="repairs",
        title="Repairs & good state of repair",
        right=(
            "Your landlord must keep the unit and the whole building in a good "
            "state of repair, fit to live in, and meeting all health, safety and "
            "maintenance standards — regardless of whether you knew about a "
            "problem before you moved in."
        ),
        legal_basis="Residential Tenancies Act, 2006 s.20 (landlord's responsibility to repair).",
        source="ontario.ca/laws/statute/06r17 (s.20); LTB Interpretation Guideline 5",
        what_you_can_do=(
            "Put every repair request in writing and keep dated copies.",
            "Take photos/video of the problem as evidence.",
            "Call 311 to report a Toronto property-standards violation; the City "
            "can issue a Notice of Violation / work order.",
            "Apply to the LTB with Form T6 — it can order repairs, a rent "
            "abatement, and compensation (up to $50,000).",
        ),
        escalation="Document → written request → City 311 (property standards) → LTB T6.",
    ),
    "pests": Right(
        topic="pests",
        title="Pest control (cockroaches, mice, bed bugs)",
        right=(
            "Pest control is the landlord's responsibility. A unit or building "
            "with an infestation is not 'fit for habitation', and the landlord "
            "must arrange professional treatment — you should not be left to pay "
            "for or fix it yourself."
        ),
        legal_basis=(
            "Residential Tenancies Act, 2006 s.20; Toronto property-standards and "
            "RentSafeTO requirements (documented pest-control program)."
        ),
        source="ontario.ca/laws/statute/06r17 (s.20); toronto.ca — RentSafeTO",
        what_you_can_do=(
            "Report the pests to the landlord in writing right away.",
            "Keep evidence (photos, dates, any pest-control notices posted).",
            "Ask to see the building's pest-control log (landlords must keep "
            "one under RentSafeTO).",
            "Call 311 if the landlord doesn't act; apply to the LTB (T6) for "
            "treatment orders and a rent abatement.",
        ),
        escalation="Report in writing → request pest-control log → City 311 → LTB T6.",
    ),
    "security": Right(
        topic="security",
        title="Locks, entry doors & security",
        right=(
            "The landlord must maintain the building's security — working "
            "entrance-door locks, intercoms and common-area lighting are part of "
            "keeping the complex in a good state of repair. Only the landlord may "
            "change locks, and they must give you a key."
        ),
        legal_basis="Residential Tenancies Act, 2006 s.20 & s.24; Toronto property standards.",
        source="ontario.ca/laws/statute/06r17 (s.20, s.24); toronto.ca property standards",
        what_you_can_do=(
            "Report broken locks, doors or buzzers in writing immediately — "
            "treat these as urgent.",
            "Call 311 for a property-standards inspection if it isn't fixed.",
            "Apply to the LTB (T6) for repair orders and compensation.",
        ),
        escalation="Urgent written notice → City 311 → LTB T6.",
    ),
    "records": Right(
        topic="records",
        title="Building records & information",
        right=(
            "Under Toronto's RentSafeTO bylaw, landlords of apartment buildings "
            "(3+ storeys, 10+ units) must keep records such as maintenance logs, "
            "a pest-control program, and vital-service and state-of-good-repair "
            "plans, and must post key information for tenants. Weak record-keeping "
            "is itself a bylaw issue and makes it harder for a landlord to defend "
            "neglect."
        ),
        legal_basis="City of Toronto Municipal Code Ch.354 (Apartment Buildings / RentSafeTO).",
        source="toronto.ca — RentSafeTO building-owner requirements",
        what_you_can_do=(
            "Ask the landlord/superintendent to see the relevant logs and plans.",
            "Look up the building's evaluation and any open work on the City's "
            "RentSafeTO portal.",
            "Report missing records or postings to 311.",
        ),
        escalation="Request records → City 311 (RentSafeTO/MLS) → cite gaps in any LTB application.",
    ),
}


# Map a risk report's red flags / groups to the rights that apply.
_CATEGORY_TOPICS: dict[str, tuple[str, ...]] = {
    "COMMON AREA PESTS": ("pests",),
    "PEST CONTROL LOG": ("pests", "records"),
    "GARBAGE/COMPACTOR ROOM": ("pests", "repairs"),
    "VITAL SERVICE PLAN": ("heat", "vital_services", "records"),
    "ELECTRICAL SERVICES / OUTLETS": ("vital_services", "repairs"),
    "ELECTRICAL SAFETY PLAN": ("vital_services", "records"),
    "WINDOWS": ("heat", "repairs"),
    "EXTERIOR DOORS": ("security",),
    "INTERCOM": ("security",),
    "STAIRWELL LIGHTING": ("security", "repairs"),
    "INT. LOBBY / HALLWAY LIGHTING": ("security", "repairs"),
    "MAINTENANCE LOG": ("repairs", "records"),
    "TENANT SERVICE REQUEST LOG": ("repairs", "records"),
    "CLEANING LOG": ("records",),
    "STATE OF GOOD REPAIR PLAN": ("repairs", "records"),
    "MAIL RECEPTACLES": ("security",),
}
_GROUP_TOPICS: dict[str, tuple[str, ...]] = {
    "Security & Safety": ("security",),
    "Pests & Sanitation": ("pests",),
    "Essential Services & Records": ("records", "repairs"),
    "Building Integrity": ("repairs",),
}


@dataclass(frozen=True, slots=True)
class Resource:
    name: str
    what: str
    contact: str
    url: str


RESOURCES: tuple[Resource, ...] = (
    Resource(
        "City of Toronto 311",
        "Report no heat, pests, or property-standards violations; the City can "
        "inspect and order repairs (RentSafeTO / Municipal Licensing & Standards).",
        "Call 311 (or 416-392-2489)",
        "https://www.toronto.ca/community-people/housing-shelter/rental-housing-rights-information/",
    ),
    Resource(
        "FMTA Tenant Hotline",
        "Free, confidential tenant-rights counselling for Toronto renters.",
        "416-921-9494",
        "https://www.torontotenants.org/hotline",
    ),
    Resource(
        "Landlord and Tenant Board (LTB)",
        "File a Tenant Application about Maintenance (Form T6) or about your "
        "rights (Form T2). Hearings are by the Tribunals Ontario Portal.",
        "Tribunals Ontario / LTB",
        "https://tribunalsontario.ca/ltb/",
    ),
    Resource(
        "Steps to Justice",
        "Plain-language, step-by-step guides to Ontario housing law (by CLEO).",
        "stepstojustice.ca",
        "https://stepstojustice.ca/legal-topic/housing-law/",
    ),
    Resource(
        "Community legal clinics / Legal Aid Ontario",
        "Free legal help for lower-income tenants, including newcomers; many "
        "clinics offer multilingual support.",
        "Legal Aid Ontario",
        "https://www.legalaid.on.ca/legal-clinics/",
    ),
)

ESCALATION_LADDER: tuple[str, ...] = (
    "1. Document everything — photos, dates, and a written log of the problem.",
    "2. Tell the landlord in writing (text/email is fine) and keep a copy.",
    "3. If it isn't fixed, call 311 — the City can inspect and issue a work order.",
    "4. Get free advice from the FMTA Tenant Hotline (416-921-9494) or a legal clinic.",
    "5. Apply to the Landlord and Tenant Board (Form T6 for maintenance, T2 for "
    "rights) — it can order repairs, compensation and a rent abatement.",
)


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------
def topics_for(report: RiskReport) -> list[str]:
    """Return the relevant rights topics for a report, most-severe first."""
    topics: list[str] = []
    for flag in report.red_flags:
        keys = ()
        if flag.category_key and flag.category_key in _CATEGORY_TOPICS:
            keys = _CATEGORY_TOPICS[flag.category_key]
        elif flag.group and flag.group in _GROUP_TOPICS:
            keys = _GROUP_TOPICS[flag.group]
        elif flag.code == "derived:reactive":
            keys = ("repairs",)
        elif flag.code == "derived:records":
            keys = ("records", "repairs")
        for k in keys:
            if k not in topics:
                topics.append(k)
    return topics


def relevant_rights(report: RiskReport) -> list[Right]:
    """The Right objects that apply to this building's issues."""
    return [RIGHTS[t] for t in topics_for(report) if t in RIGHTS]


def grounding_context(report: RiskReport) -> str:
    """Build an authoritative legal brief for the Advocate agent's RAG context.

    Only the rights relevant to *this* building are included, so the agent is
    anchored to accurate, citeable facts rather than generalities.
    """
    rights = relevant_rights(report)
    lines: list[str] = [
        "AUTHORITATIVE ONTARIO/TORONTO TENANT-LAW REFERENCE "
        "(use only these facts for legal statements; cite the basis; do not invent law):",
        "",
    ]
    if not rights:
        # Always give the agent the repair baseline.
        rights = [RIGHTS["repairs"]]
    for r in rights:
        lines.append(f"### {r.title}")
        lines.append(f"- Right: {r.right}")
        lines.append(f"- Legal basis: {r.legal_basis}")
        lines.append(f"- What a tenant can do: {' '.join(r.what_you_can_do)}")
        lines.append(f"- Source: {r.source}")
        lines.append("")
    lines.append("ESCALATION LADDER (general): " + " ".join(ESCALATION_LADDER))
    lines.append("")
    lines.append(
        "KEY RESOURCES: "
        + "; ".join(f"{x.name} — {x.contact}" for x in RESOURCES)
    )
    lines.append("")
    lines.append(f"DISCLAIMER (always include): {DISCLAIMER}")
    return "\n".join(lines)


def compact_grounding(report: RiskReport) -> str:
    """A short legal reference (fewer tokens) for latency-sensitive agent calls."""
    rights = relevant_rights(report) or [RIGHTS["repairs"]]
    parts = [
        "AUTHORITATIVE TENANT-LAW FACTS (cite the basis; never invent law):",
    ]
    for r in rights:
        parts.append(f"- {r.title} [{r.legal_basis}]: {r.right} First step: {r.what_you_can_do[0]}")
    parts.append(
        "RESOURCES: City of Toronto 311 (no heat/pests/standards); FMTA Tenant "
        "Hotline 416-921-9494; Landlord and Tenant Board Form T6 (maintenance, up "
        "to $50,000); Steps to Justice."
    )
    parts.append(f"DISCLAIMER: {DISCLAIMER}")
    return "\n".join(parts)
