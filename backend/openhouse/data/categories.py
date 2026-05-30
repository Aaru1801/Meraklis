"""Canonical taxonomy for the RentSafeTO building-evaluation categories.

The City of Toronto's RentSafeTO program scores apartment buildings (3+
storeys, 10+ units) across ~50 inspection categories. Each category is graded
on a 1-3 scale (3 = good, 2 = adequate, 1 = poor) or "N/A" when it does not
apply to the building.

A raw "1" in a spreadsheet means nothing to a newcomer. The value OpenHouse
adds is *context*: which categories actually affect a tenant's safety, health
and habitability, how heavily to weight them, and — in plain language — what a
low score means for the person who would live there.

Every ``key`` below matches the exact column name returned by the City's CKAN
datastore API, so lookups against a raw record never need fuzzy matching.

Source: City of Toronto Open Data — "Apartment Building Evaluation"
        https://open.toronto.ca/dataset/apartment-building-evaluation/
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Group(str, Enum):
    """Thematic grouping used for the risk report's section breakdown."""

    SECURITY = "Security & Safety"
    PESTS = "Pests & Sanitation"
    ESSENTIAL = "Essential Services & Records"
    INTEGRITY = "Building Integrity"
    COMMON = "Common Areas"
    GROUNDS = "Exterior & Grounds"


@dataclass(frozen=True, slots=True)
class Category:
    """One RentSafeTO inspection category, enriched with tenant context.

    Attributes:
        key: Exact CKAN column name (e.g. ``"COMMON AREA PESTS"``).
        label: Human-friendly display name.
        group: Thematic group for the report.
        weight: Relative importance, 1 (cosmetic) to 5 (safety-critical).
            Used to weight category scores when computing sub-scores.
        newcomer_critical: True for issues that disproportionately harm
            newcomers — things they may not know to check, or that are
            hardest to recover from without a local support network
            (heat/vital services in winter, security, pest infestations,
            and whether management even keeps the legally required records).
        tenant_impact: What a *low* (1/3) score actually means for a renter,
            in plain language. This is the line we surface in the UI.
    """

    key: str
    label: str
    group: Group
    weight: int
    newcomer_critical: bool
    tenant_impact: str


# ---------------------------------------------------------------------------
# The taxonomy. Order roughly follows the City's inspection sheet.
# ---------------------------------------------------------------------------

CATEGORIES: tuple[Category, ...] = (
    # --- Security & Safety -------------------------------------------------
    Category(
        "INTERCOM", "Intercom / entry system", Group.SECURITY, 4, True,
        "A broken intercom or door-entry system means strangers can follow you "
        "into the building. For ground-floor and elevator-access units this is a "
        "direct personal-safety risk.",
    ),
    Category(
        "EXTERIOR DOORS", "Secure exterior doors", Group.SECURITY, 5, True,
        "Exterior doors that don't latch or lock let anyone into the building. "
        "This is one of the most common precursors to theft and assault in "
        "apartment buildings.",
    ),
    Category(
        "EMERGENCY CONTACT SIGN", "Emergency contact signage", Group.SECURITY, 3, True,
        "Without posted emergency and after-hours contact information, you have no "
        "fast way to reach the landlord when the heat fails at night or a pipe "
        "bursts on a weekend.",
    ),
    Category(
        "BALCONY GUARDS", "Balcony guards / railings", Group.SECURITY, 5, False,
        "Loose or low balcony guards are a fall hazard, especially dangerous for "
        "families with young children.",
    ),
    Category(
        "INT. HANDRAIL / GUARD - SAFETY", "Stair handrail safety", Group.SECURITY, 4, False,
        "Wobbly or missing stair guards and handrails cause falls — a serious "
        "concern for seniors and anyone carrying a child or groceries.",
    ),
    Category(
        "STAIRWELL LIGHTING", "Stairwell lighting", Group.SECURITY, 4, True,
        "Dark stairwells are both a trip hazard and a place where people feel "
        "unsafe. Burnt-out stairwell lighting is a sign maintenance requests are "
        "being ignored.",
    ),
    Category(
        "INT. LOBBY / HALLWAY LIGHTING", "Lobby & hallway lighting", Group.SECURITY, 3, True,
        "Poorly lit hallways make residents feel unsafe and often indicate the "
        "landlord is slow to replace fixtures.",
    ),
    Category(
        "ELECTRICAL SERVICES / OUTLETS", "Electrical services & outlets", Group.SECURITY, 5, False,
        "Faulty common-area wiring and outlets are a fire risk for the entire "
        "building, not just one unit.",
    ),

    # --- Pests & Sanitation ------------------------------------------------
    Category(
        "COMMON AREA PESTS", "Pest activity in common areas", Group.PESTS, 5, True,
        "Visible cockroaches, mice or bed-bug evidence in shared spaces strongly "
        "predicts pests inside units. Infestations are expensive, stressful, and "
        "very hard to get a landlord to treat once you've moved in.",
    ),
    Category(
        "BUILDING CLEANLINESS", "General cleanliness", Group.PESTS, 3, False,
        "Persistent dirt and garbage in common areas signals a building that "
        "isn't being properly maintained or cleaned on schedule.",
    ),
    Category(
        "GARBAGE/COMPACTOR ROOM", "Garbage / compactor room", Group.PESTS, 4, True,
        "Overflowing or filthy garbage rooms attract pests and create odours and "
        "health hazards that spread through the building.",
    ),
    Category(
        "CHUTE ROOMS - MAINTENANCE", "Garbage chute rooms", Group.PESTS, 3, False,
        "Neglected chute rooms are a common entry point for pests and a source of "
        "smells on every floor.",
    ),

    # --- Essential Services & Records --------------------------------------
    Category(
        "VITAL SERVICE PLAN", "Vital service (heat/water) plan", Group.ESSENTIAL, 5, True,
        "Landlords must have a plan to maintain heat, hot/cold water and "
        "electricity. A low score here means the building may not be ready to "
        "restore heat or water quickly when something fails — dangerous in a "
        "Toronto winter.",
    ),
    Category(
        "ELECTRICAL SAFETY PLAN", "Electrical safety plan", Group.ESSENTIAL, 4, False,
        "A missing electrical safety plan means no organized approach to "
        "preventing electrical fires and hazards.",
    ),
    Category(
        "STATE OF GOOD REPAIR PLAN", "Capital repair plan", Group.ESSENTIAL, 4, True,
        "Without a state-of-good-repair plan, the landlord has no roadmap for "
        "fixing aging elevators, roofs and boilers — so problems tend to be left "
        "until they fail.",
    ),
    Category(
        "MAINTENANCE LOG", "Maintenance log", Group.ESSENTIAL, 4, True,
        "A poor maintenance log means repair requests aren't being tracked. If "
        "you report a problem, there's a real chance it simply gets forgotten.",
    ),
    Category(
        "CLEANING LOG", "Cleaning log", Group.ESSENTIAL, 2, False,
        "No cleaning log usually means cleaning happens irregularly, if at all.",
    ),
    Category(
        "PEST CONTROL LOG", "Pest control log", Group.ESSENTIAL, 5, True,
        "A missing pest-control log means the building isn't doing scheduled, "
        "documented pest treatment — the single biggest reason infestations get "
        "out of control before anyone acts.",
    ),
    Category(
        "TENANT SERVICE REQUEST LOG", "Tenant service request log", Group.ESSENTIAL, 4, True,
        "If tenant service requests aren't logged, there's no paper trail when "
        "your repair is ignored — which makes it far harder to escalate to the "
        "Landlord and Tenant Board later.",
    ),
    Category(
        "TENANT NOTIFICATION BOARD", "Tenant notification board", Group.ESSENTIAL, 2, True,
        "The notice board is how tenants learn about water shut-offs, pest "
        "treatments and their rights. A neglected board means poor communication.",
    ),

    # --- Building Integrity ------------------------------------------------
    Category(
        "BUILDING EXTERIOR", "Building exterior / facade", Group.INTEGRITY, 4, False,
        "Crumbling brick, spalling concrete or damaged cladding can mean water "
        "getting into walls — leading to mould and, in older towers, falling "
        "debris.",
    ),
    Category(
        "WINDOWS", "Windows", Group.INTEGRITY, 4, True,
        "Drafty, broken or painted-shut windows mean high heating bills, cold "
        "units in winter and no ventilation in summer.",
    ),
    Category(
        "ELEVATOR MAINTENANCE", "Elevator maintenance", Group.INTEGRITY, 4, True,
        "Unreliable elevators are a serious hardship for seniors, people with "
        "disabilities, families with strollers and anyone on a high floor.",
    ),
    Category(
        "COMMON AREA VENTILATION", "Common area ventilation", Group.INTEGRITY, 3, False,
        "Poor ventilation traps humidity and odours and contributes to mould in "
        "hallways and shared spaces.",
    ),
    Category(
        "STAIRWELL - WALLS AND CEILING", "Stairwell structure", Group.INTEGRITY, 3, False,
        "Damaged stairwell walls and ceilings can indicate water damage and "
        "deferred structural maintenance on the building's primary fire exit.",
    ),
    Category(
        "STAIRWELL - LANDING AND STEPS", "Stair landings & steps", Group.INTEGRITY, 4, False,
        "Cracked or uneven stairs on the main emergency exit are both a daily "
        "trip hazard and a danger during an evacuation.",
    ),
    Category(
        "INT. HALLWAY - WALLS / CEILING", "Hallway walls & ceilings", Group.INTEGRITY, 2, False,
        "Stained or damaged hallway ceilings often reveal ongoing leaks from "
        "above.",
    ),
    Category(
        "INTERIOR HALLWAY FLOORS", "Hallway floors", Group.INTEGRITY, 2, False,
        "Torn or buckled hallway flooring is a trip hazard and a sign of deferred "
        "maintenance.",
    ),
    Category(
        "CATCH BASINS / STORM DRAINAGE", "Storm drainage", Group.INTEGRITY, 3, False,
        "Blocked drainage leads to flooding in garages, lockers and ground-floor "
        "units during heavy rain.",
    ),
    Category(
        "RETAINING WALLS", "Retaining walls", Group.INTEGRITY, 2, False,
        "Failing retaining walls are a slow but real structural and safety "
        "concern on sloped sites.",
    ),

    # --- Common Areas (lower-stakes upkeep) --------------------------------
    Category(
        "LOBBY - WALLS AND CEILING", "Lobby walls & ceiling", Group.COMMON, 1, False,
        "Lobby condition is mostly cosmetic but reflects overall pride of "
        "ownership.",
    ),
    Category(
        "LOBBY FLOORS", "Lobby floors", Group.COMMON, 1, False,
        "Worn lobby floors are cosmetic, but damaged surfaces can be a slip "
        "hazard when wet.",
    ),
    Category(
        "LAUNDRY ROOM", "Laundry room", Group.COMMON, 2, False,
        "A poorly kept laundry room often means broken machines and lost money — "
        "a real inconvenience if you don't have in-unit laundry.",
    ),
    Category(
        "MAIL RECEPTACLES", "Mailboxes", Group.COMMON, 2, True,
        "Broken or insecure mailboxes put your mail — including immigration and "
        "government documents — at risk of theft.",
    ),
    Category(
        "ELEVATOR COSMETICS", "Elevator interior condition", Group.COMMON, 1, False,
        "Cosmetic only, but consistently shabby elevators reflect low maintenance "
        "investment.",
    ),
    Category(
        "GRAFFITI", "Graffiti", Group.COMMON, 1, False,
        "Unaddressed graffiti is mostly cosmetic but signals slow upkeep.",
    ),
    Category(
        "EXT. RECEPTACLE STORAGE AREA", "Exterior bin storage", Group.COMMON, 2, False,
        "Messy outdoor bin areas attract pests and create odours near entrances.",
    ),
    Category(
        "INT. RECEPTACLE STORAGE AREA", "Interior bin storage", Group.COMMON, 2, False,
        "Interior garbage storage problems contribute to pests and smells inside "
        "the building.",
    ),
    Category(
        "STORAGE AREAS/LOCKERS MAINT.", "Storage lockers", Group.COMMON, 1, False,
        "Damaged or insecure lockers put stored belongings at risk.",
    ),

    # --- Exterior & Grounds ------------------------------------------------
    Category(
        "EXTERIOR GROUNDS", "Exterior grounds", Group.GROUNDS, 2, False,
        "Neglected grounds (overgrowth, debris) reflect overall upkeep and can "
        "hide pest harbourage.",
    ),
    Category(
        "FENCING", "Fencing", Group.GROUNDS, 2, False,
        "Damaged perimeter fencing reduces security and can be a hazard.",
    ),
    Category(
        "EXTERIOR WALKWAYS", "Exterior walkways", Group.GROUNDS, 3, True,
        "Cracked or icy walkways are a major slip-and-fall hazard, especially in "
        "winter for newcomers unused to Canadian ice.",
    ),
    Category(
        "PARKING AREAS", "Parking areas", Group.GROUNDS, 2, False,
        "Poorly maintained or unlit parking areas are a security and safety "
        "concern after dark.",
    ),
    Category(
        "ABANDONED EQUIP./DERELICT VEH.", "Abandoned vehicles / equipment", Group.GROUNDS, 1, False,
        "Derelict vehicles and equipment on site attract pests and signal "
        "neglect.",
    ),
    Category(
        "NUMBERING OF PROPERTY", "Property address numbering", Group.GROUNDS, 2, False,
        "Missing or unclear address numbers delay emergency services (fire, "
        "ambulance, police) finding the building.",
    ),
)

# Categories that appear in some records but carry little tenant signal; kept
# out of weighting but still displayed if present.
NEUTRAL_KEYS: frozenset[str] = frozenset({
    "POOLS",
    "OTHER AMENITIES",
    "ACCESSORY BUILDINGS",
    "CLOTHING DROP BOXES",
})

# Fast lookup tables -------------------------------------------------------
BY_KEY: dict[str, Category] = {c.key: c for c in CATEGORIES}

NEWCOMER_CRITICAL_KEYS: frozenset[str] = frozenset(
    c.key for c in CATEGORIES if c.newcomer_critical
)

# All the per-area score columns we recognize (canonical + neutral).
ALL_CATEGORY_KEYS: frozenset[str] = frozenset(BY_KEY) | NEUTRAL_KEYS


def group_of(key: str) -> Group | None:
    """Return the thematic group for a category key, if recognized."""
    cat = BY_KEY.get(key)
    return cat.group if cat else None


def categories_in(group: Group) -> list[Category]:
    """All recognized categories belonging to ``group``."""
    return [c for c in CATEGORIES if c.group is group]
