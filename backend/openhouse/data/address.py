"""Address normalization & reconciliation (the validation routine).

Heterogeneous housing sources spell the same address many ways: "1182 Queen
Street West", "1182 QUEEN ST W", "1182 Queen St. W.". Before any cross-source
analysis, addresses must be reconciled to a canonical form so records for the
*same* building line up.

This module provides:
- ``normalize_address`` → a structured :class:`NormalizedAddress`.
- ``address_key`` → a stable, comparable key ("1182 queen st w").
- ``match_score`` / ``addresses_match`` → fuzzy reconciliation between two
  raw address strings, tolerant of "Street" vs "St", direction abbreviations,
  punctuation and unit prefixes.

Pure stdlib — no network, no dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Canonical street-type abbreviations (Canada Post / municipal conventions).
STREET_TYPES: dict[str, str] = {
    "STREET": "ST", "ST": "ST",
    "AVENUE": "AVE", "AVE": "AVE", "AV": "AVE",
    "ROAD": "RD", "RD": "RD",
    "BOULEVARD": "BLVD", "BLVD": "BLVD", "BOUL": "BLVD",
    "DRIVE": "DR", "DR": "DR",
    "CRESCENT": "CRES", "CRES": "CRES",
    "COURT": "CRT", "CRT": "CRT", "CT": "CRT",
    "PLACE": "PL", "PL": "PL",
    "LANE": "LANE", "LN": "LANE",
    "TERRACE": "TER", "TER": "TER", "TERR": "TER",
    "TRAIL": "TRL", "TRL": "TRL",
    "GARDENS": "GDNS", "GDNS": "GDNS",
    "SQUARE": "SQ", "SQ": "SQ",
    "CIRCLE": "CIR", "CIR": "CIR",
    "PARKWAY": "PKWY", "PKWY": "PKWY",
    "HIGHWAY": "HWY", "HWY": "HWY",
    "WAY": "WAY",
    "GROVE": "GRV", "GRV": "GRV",
    "HEIGHTS": "HTS", "HTS": "HTS",
    "GATE": "GATE",
    "PATH": "PATH",
    "MEWS": "MEWS",
    "CLOSE": "CLOSE",
    "HILL": "HILL",
    "PARK": "PARK",
}

# Directions (pre- or post-directional).
DIRECTIONS: dict[str, str] = {
    "NORTH": "N", "N": "N",
    "SOUTH": "S", "S": "S",
    "EAST": "E", "E": "E",
    "WEST": "W", "W": "W",
    "NORTHEAST": "NE", "NE": "NE",
    "NORTHWEST": "NW", "NW": "NW",
    "SOUTHEAST": "SE", "SE": "SE",
    "SOUTHWEST": "SW", "SW": "SW",
}

UNIT_MARKERS = {"UNIT", "APT", "APARTMENT", "SUITE", "STE", "#"}

_PUNCT = re.compile(r"[.,]")
_WS = re.compile(r"\s+")


@dataclass(slots=True)
class NormalizedAddress:
    """A structured, canonicalized address."""

    raw: str
    unit: str | None = None
    street_number: str | None = None
    street_name: str = ""
    street_type: str | None = None
    direction: str | None = None
    canonical: str = ""  # e.g. "1182 QUEEN ST W"
    tokens: list[str] = field(default_factory=list)
    confidence: float = 1.0  # parsing confidence (lower if it looked malformed)

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "unit": self.unit,
            "street_number": self.street_number,
            "street_name": self.street_name,
            "street_type": self.street_type,
            "direction": self.direction,
            "canonical": self.canonical,
            "confidence": round(self.confidence, 2),
        }


def _clean(text: str) -> str:
    text = _PUNCT.sub(" ", text or "")
    return _WS.sub(" ", text).strip().upper()


def normalize_address(raw: str) -> NormalizedAddress:
    """Parse and canonicalize a raw address string.

    Handles unit prefixes ("Unit 5 - 1182 ..."), unit suffixes, street-type
    expansion ("Street"→"ST"), and directionals ("West"→"W").
    """
    cleaned = _clean(raw)
    addr = NormalizedAddress(raw=raw)
    if not cleaned:
        addr.confidence = 0.0
        return addr

    # Split off a leading "UNIT 5 -" / "5 -" style unit reference.
    # Pattern: optional unit marker, then "<unit> - <rest>".
    dash_split = re.split(r"\s*[-–]\s*", cleaned, maxsplit=1)
    if len(dash_split) == 2 and re.match(r"^(UNIT|APT|APARTMENT|SUITE|STE|#)?\s*\w+$", dash_split[0]):
        left = dash_split[0]
        m = re.search(r"(\w+)$", left)
        if m:
            addr.unit = m.group(1)
        cleaned = dash_split[1].strip()

    tokens = cleaned.split()

    # Trailing unit: "... UNIT 502" / "... #502" / "... # 502" / "... APT 3B"
    for i in range(len(tokens)):
        t = tokens[i]
        if t.startswith("#") and len(t) > 1:  # "#1201" — marker+value in one token
            addr.unit = t.lstrip("#")
            tokens = tokens[:i]
            break
        if (t in UNIT_MARKERS or t == "#") and i + 1 < len(tokens):
            addr.unit = tokens[i + 1].lstrip("#")
            tokens = tokens[:i]
            break

    if not tokens:
        addr.confidence = 0.3
        addr.canonical = cleaned
        addr.tokens = cleaned.split()
        return addr

    # Leading street number (may contain a letter or range, e.g. "12A", "12-14").
    if re.match(r"^\d+[A-Z]?(-\d+[A-Z]?)?$", tokens[0]):
        addr.street_number = tokens[0]
        tokens = tokens[1:]

    # Trailing direction.
    if tokens and tokens[-1] in DIRECTIONS:
        addr.direction = DIRECTIONS[tokens[-1]]
        tokens = tokens[:-1]

    # Trailing street type.
    if tokens and tokens[-1] in STREET_TYPES:
        addr.street_type = STREET_TYPES[tokens[-1]]
        tokens = tokens[:-1]

    addr.street_name = " ".join(tokens).strip()

    # Reassemble canonical form.
    parts = [
        p
        for p in (
            addr.street_number,
            addr.street_name,
            addr.street_type,
            addr.direction,
        )
        if p
    ]
    addr.canonical = " ".join(parts)
    addr.tokens = addr.canonical.split()
    if not addr.street_number or not addr.street_name:
        addr.confidence = 0.6  # parsed, but incomplete
    return addr


def address_key(raw: str) -> str:
    """A lowercase canonical key for grouping/matching the same building."""
    return normalize_address(raw).canonical.lower()


def match_score(a: str, b: str) -> float:
    """Similarity in [0, 1] between two raw addresses after normalization.

    1.0 = same street number + same canonical street tokens. Partial credit for
    matching the number and most tokens (tolerates type/direction differences).
    """
    na, nb = normalize_address(a), normalize_address(b)
    if not na.canonical or not nb.canonical:
        return 0.0
    if na.canonical == nb.canonical:
        return 1.0

    # Street number must match for a meaningful comparison.
    if na.street_number and nb.street_number and na.street_number != nb.street_number:
        return 0.0

    set_a, set_b = set(na.tokens), set(nb.tokens)
    if not set_a or not set_b:
        return 0.0
    jaccard = len(set_a & set_b) / len(set_a | set_b)
    # Bonus if street_name core matches exactly.
    name_bonus = 0.15 if na.street_name and na.street_name == nb.street_name else 0.0
    return min(1.0, jaccard + name_bonus)


def addresses_match(a: str, b: str, threshold: float = 0.7) -> bool:
    """True if two raw addresses likely refer to the same building."""
    return match_score(a, b) >= threshold
